from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse

from app.videos.contracts import (
    ExtractionStatus,
    VideoAuthor,
    VideoContentResponse,
    VideoPlatform,
)
from app.videos.errors import ContentUnavailableError

_VIDEO_ID_PATTERN = re.compile(r"/(?:share/)?video/(\d+)")
_ROUTER_DATA_MARKERS = ("window._ROUTER_DATA =", "window._ROUTER_DATA=")


@dataclass(frozen=True, slots=True)
class DouyinParseResult:
    content: VideoContentResponse
    playback_source_url: str | None


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metadata: dict[str, str] = {}
        self.scripts: dict[str, list[str]] = {}
        self._current_script_id: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta":
            key = attributes.get("property") or attributes.get("name")
            content = attributes.get("content")
            if key and content:
                self.metadata[key.lower()] = content.strip()
        elif tag == "script":
            script_id = attributes.get("id")
            if script_id:
                self._current_script_id = script_id
                self.scripts.setdefault(script_id, [])

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._current_script_id = None

    def handle_data(self, data: str) -> None:
        if self._current_script_id:
            self.scripts[self._current_script_id].append(data)


def _iter_nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nodes(child)


def _decode_json(value: str) -> Any | None:
    candidates = (value, unquote(value))
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _router_data(html: str) -> Any | None:
    decoder = json.JSONDecoder()
    for marker in _ROUTER_DATA_MARKERS:
        start = html.find(marker)
        if start < 0:
            continue
        payload = html[start + len(marker) :].lstrip()
        try:
            value, _ = decoder.raw_decode(payload)
            return value
        except json.JSONDecodeError:
            continue
    return None


def _find_aweme_detail(states: list[Any]) -> dict[str, Any] | None:
    for state in states:
        if state is None:
            continue
        for node in _iter_nodes(state):
            for key in ("aweme_detail", "awemeDetail"):
                detail = node.get(key)
                if isinstance(detail, dict):
                    return detail
            if node.get("aweme_id") and any(key in node for key in ("desc", "video", "author")):
                return node
    return None


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _media_url(value: Any) -> str | None:
    if isinstance(value, str):
        return value or None
    if isinstance(value, list):
        return _first_string(*value)
    if isinstance(value, dict):
        return _media_url(value.get("url_list") or value.get("urlList") or value.get("uri"))
    return None


def _duration_seconds(value: Any) -> float | None:
    if not isinstance(value, int | float) or value <= 0:
        return None
    return round(float(value) / 1000, 3) if value > 1000 else float(value)


def _prefer_no_watermark_playback(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if not (
        parsed.scheme == "https"
        and (hostname == "snssdk.com" or hostname.endswith(".snssdk.com"))
        and parsed.path == "/aweme/v1/playwm/"
    ):
        return url

    query = parse_qs(parsed.query)
    video_ids = query.get("video_id", [])
    if not video_ids or not video_ids[0]:
        return url
    params = {
        "video_id": video_ids[0],
        "ratio": (query.get("ratio") or ["1080p"])[0],
        "line": (query.get("line") or ["0"])[0],
        "is_play_url": "1",
        "watermark": "0",
        "source": "PackSourceEnum_PUBLISH",
    }
    return urlunparse(
        parsed._replace(
            path="/aweme/v1/play/",
            query=urlencode(params),
            fragment="",
        )
    )


def _highest_quality_playback(video: dict[str, Any]) -> str | None:
    bit_rates = video.get("bit_rate")
    candidates: list[tuple[int, int, str]] = []
    if isinstance(bit_rates, list):
        for entry in bit_rates:
            if not isinstance(entry, dict):
                continue
            play_addr = entry.get("play_addr")
            if not isinstance(play_addr, dict):
                continue
            url = _media_url(play_addr)
            if not url:
                continue
            try:
                width = int(play_addr.get("width") or entry.get("width") or 0)
                height = int(play_addr.get("height") or entry.get("height") or 0)
                bit_rate = int(entry.get("bit_rate") or 0)
            except (TypeError, ValueError):
                width = height = bit_rate = 0
            candidates.append((width * height, bit_rate, url))
    if candidates:
        selected = max(candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]
        return _prefer_no_watermark_playback(selected)
    return _prefer_no_watermark_playback(
        _media_url(
            video.get("play_addr")
            or video.get("playAddr")
            or video.get("download_addr")
            or video.get("downloadAddr")
        )
    )


class DouyinPageParser:
    """Normalize public Douyin page state behind one parser interface."""

    def parse(
        self,
        html: str,
        *,
        source_url: str,
        final_url: str,
    ) -> DouyinParseResult:
        parser = _MetadataParser()
        parser.feed(html)

        states: list[Any] = [_router_data(html)]
        for script_id in ("RENDER_DATA", "__NEXT_DATA__"):
            script = "".join(parser.scripts.get(script_id, []))
            if script:
                states.append(_decode_json(script))

        detail = _find_aweme_detail(states) or {}
        video = detail.get("video") if isinstance(detail.get("video"), dict) else {}
        author = detail.get("author") if isinstance(detail.get("author"), dict) else {}

        title = _first_string(
            detail.get("desc"),
            parser.metadata.get("og:title"),
            parser.metadata.get("twitter:title"),
        )
        if title:
            title = re.sub(r"\s*[-—|]\s*抖音\s*$", "", title).strip()
        if not title:
            raise ContentUnavailableError("没有找到可用的视频内容，链接可能已失效或不是公开视频。")

        canonical_url = _first_string(parser.metadata.get("og:url"), final_url) or final_url
        video_id_match = _VIDEO_ID_PATTERN.search(canonical_url) or _VIDEO_ID_PATTERN.search(
            final_url
        )
        video_id = _first_string(detail.get("aweme_id"))
        if not video_id and video_id_match:
            video_id = video_id_match.group(1)

        cover = _media_url(
            video.get("cover")
            or video.get("origin_cover")
            or video.get("originCover")
            or parser.metadata.get("og:image")
        )
        avatar = _media_url(author.get("avatar_thumb") or author.get("avatarThumb"))
        playback_source_url = _prefer_no_watermark_playback(
            _media_url(
                video.get("play_addr")
                or video.get("playAddr")
                or video.get("download_addr")
                or video.get("downloadAddr")
            )
        )
        playback_url = (
            f"/api/videos/{video_id}/playback" if video_id and playback_source_url else None
        )

        return DouyinParseResult(
            content=VideoContentResponse(
                platform=VideoPlatform.DOUYIN,
                status=ExtractionStatus.METADATA,
                source_url=source_url,
                canonical_url=canonical_url,
                video_id=video_id,
                title=title,
                description=_first_string(
                    parser.metadata.get("og:description"),
                    detail.get("desc"),
                ),
                author=VideoAuthor(
                    name=_first_string(author.get("nickname"), parser.metadata.get("author")),
                    avatar_url=avatar,
                ),
                cover_url=cover,
                playback_url=playback_url,
                duration_seconds=_duration_seconds(video.get("duration")),
                transcript=None,
                warnings=["公开视频页面没有可直接使用的字幕轨道。"],
            ),
            playback_source_url=playback_source_url,
        )

    def parse_detail(
        self,
        detail: dict[str, Any],
        *,
        source_url: str,
        video_id: str,
    ) -> DouyinParseResult:
        video = detail.get("video") if isinstance(detail.get("video"), dict) else {}
        author = detail.get("author") if isinstance(detail.get("author"), dict) else {}
        title = _first_string(detail.get("desc"))
        if not title:
            raise ContentUnavailableError("没有找到可用的视频内容，链接可能已失效或不是公开视频。")

        normalized_video_id = _first_string(detail.get("aweme_id"), video_id) or video_id
        playback_source_url = _highest_quality_playback(video)
        playback_url = (
            f"/api/videos/{normalized_video_id}/playback" if playback_source_url else None
        )

        return DouyinParseResult(
            content=VideoContentResponse(
                platform=VideoPlatform.DOUYIN,
                status=ExtractionStatus.METADATA,
                source_url=source_url,
                canonical_url=f"https://www.douyin.com/video/{normalized_video_id}",
                video_id=normalized_video_id,
                title=title,
                description=title,
                author=VideoAuthor(
                    name=_first_string(author.get("nickname")),
                    avatar_url=_media_url(author.get("avatar_thumb") or author.get("avatarThumb")),
                ),
                cover_url=_media_url(
                    video.get("cover") or video.get("origin_cover") or video.get("originCover")
                ),
                playback_url=playback_url,
                duration_seconds=_duration_seconds(video.get("duration")),
                transcript=None,
                warnings=["公开视频页面没有可直接使用的字幕轨道。"],
            ),
            playback_source_url=playback_source_url,
        )
