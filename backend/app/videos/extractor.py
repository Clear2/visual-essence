from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from collections.abc import Awaitable, Callable
from inspect import isawaitable
from time import perf_counter
from typing import Protocol
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import httpx

from app.videos.analysis import VideoAnalyzer
from app.videos.contracts import (
    ExtractionStatus,
    ProcessingStepKind,
    ProcessingStepStatus,
    ProcessingTraceStep,
    VideoContentResponse,
)
from app.videos.douyin import DouyinPageParser
from app.videos.douyin_downloader import DouyinDetailClient, DouyinDownloaderDetailClient
from app.videos.errors import (
    ContentUnavailableError,
    UnsafeVideoUrlError,
    UnsupportedPlatformError,
    UpstreamFetchError,
    VideoAnalysisError,
)

_ALLOWED_HOSTS = ("douyin.com", "iesdouyin.com")
_ALLOWED_MEDIA_HOSTS = ("douyinvod.com", "douyincdn.com", "byteimg.com", "snssdk.com")
_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_TRAILING_PUNCTUATION = "，。！？、；：,.!?;:)}]"
_VIDEO_PATH_PATTERN = re.compile(r"/(?:share/)?video/(\d+)")
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
)
_MAX_MEDIA_SOURCE_ATTEMPTS = 5


class HttpFetcher(Protocol):
    async def get(self, url: str, **kwargs: object) -> httpx.Response: ...


HostResolver = Callable[[str], Awaitable[set[str]]]
ProgressReporter = Callable[[ProcessingTraceStep], Awaitable[None] | None]


async def _report_progress(
    completed: list[ProcessingTraceStep],
    reporter: ProgressReporter | None,
    step: ProcessingTraceStep,
) -> None:
    for index, current in enumerate(completed):
        if current.key == step.key:
            completed[index] = step
            break
    else:
        completed.append(step)
    if reporter is None:
        return
    result = reporter(step)
    if isawaitable(result):
        await result


async def resolve_host(hostname: str) -> set[str]:
    def _resolve() -> set[str]:
        records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        return {record[4][0] for record in records}

    try:
        return await asyncio.to_thread(_resolve)
    except socket.gaierror as error:
        raise UpstreamFetchError("无法解析视频平台地址，请稍后重试。") from error


def _extract_url(value: str) -> str:
    match = _URL_PATTERN.search(value.strip())
    if not match:
        raise UnsupportedPlatformError("没有找到有效的视频链接。")
    return match.group(0).rstrip(_TRAILING_PUNCTUATION)


def _is_allowed_host(hostname: str) -> bool:
    normalized = hostname.lower().rstrip(".").removeprefix("www.")
    return any(normalized == host or normalized.endswith(f".{host}") for host in _ALLOWED_HOSTS)


def _is_allowed_media_host(hostname: str) -> bool:
    normalized = hostname.lower().rstrip(".")
    return any(
        normalized == host or normalized.endswith(f".{host}") for host in _ALLOWED_MEDIA_HOSTS
    )


def _extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    path_match = _VIDEO_PATH_PATTERN.search(parsed.path)
    if path_match:
        return path_match.group(1)
    modal_ids = parse_qs(parsed.query).get("modal_id", [])
    if modal_ids and modal_ids[0].isdigit():
        return modal_ids[0]
    return None


def _media_source_for_attempt(source_url: str, attempt: int) -> str:
    if attempt == 0:
        return source_url
    parsed = urlparse(source_url)
    hostname = (parsed.hostname or "").lower()
    if not (
        (hostname == "snssdk.com" or hostname.endswith(".snssdk.com"))
        and parsed.path == "/aweme/v1/play/"
    ):
        return source_url
    query = parse_qs(parsed.query)
    if not query.get("video_id"):
        return source_url
    query["line"] = [str(attempt)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


async def _ensure_safe_url(url: str, resolver: HostResolver) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeVideoUrlError("链接格式不正确，请使用完整的 HTTP 或 HTTPS 地址。")
    if not _is_allowed_host(parsed.hostname):
        raise UnsupportedPlatformError("第一期仅支持抖音，Bilibili 和 YouTube 将在后续开放。")

    addresses = await resolver(parsed.hostname)
    if not addresses:
        raise UnsafeVideoUrlError("链接目标无法验证。")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if any(
            (
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_reserved,
                ip.is_unspecified,
            )
        ):
            raise UnsafeVideoUrlError("链接目标不允许访问。")


async def _ensure_safe_media_url(
    url: str,
    resolver: HostResolver,
    *,
    require_allowlisted_host: bool = True,
) -> None:
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError as error:
        raise UnsafeVideoUrlError("视频播放地址未通过安全校验。") from error
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeVideoUrlError("视频播放地址未通过安全校验。")
    if port not in {None, 443}:
        raise UnsafeVideoUrlError("视频播放地址未通过安全校验。")
    if require_allowlisted_host and not _is_allowed_media_host(parsed.hostname):
        raise UnsafeVideoUrlError("视频播放地址未通过安全校验。")

    addresses = await resolver(parsed.hostname)
    if not addresses:
        raise UnsafeVideoUrlError("视频播放地址无法验证。")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if any(
            (
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_reserved,
                ip.is_unspecified,
            )
        ):
            raise UnsafeVideoUrlError("视频播放地址未通过安全校验。")


class VideoExtractionModule:
    """Resolve, fetch, parse, and normalize supported public video URLs."""

    def __init__(
        self,
        fetcher: HttpFetcher,
        *,
        resolver: HostResolver = resolve_host,
        max_redirects: int = 5,
        max_response_bytes: int = 5 * 1024 * 1024,
        douyin_detail_client: DouyinDetailClient | None = None,
        video_analyzer: VideoAnalyzer | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._resolver = resolver
        self._max_redirects = max_redirects
        self._max_response_bytes = max_response_bytes
        self._douyin_parser = DouyinPageParser()
        self._douyin_detail_client = douyin_detail_client or DouyinDownloaderDetailClient()
        self._video_analyzer = video_analyzer
        self._playback_sources: dict[str, str] = {}

    async def extract(
        self,
        value: str,
        *,
        on_progress: ProgressReporter | None = None,
    ) -> VideoContentResponse:
        completed_steps: list[ProcessingTraceStep] = []
        started_at = perf_counter()

        async def report(step: ProcessingTraceStep) -> None:
            await _report_progress(
                completed_steps,
                on_progress,
                step.model_copy(update={"elapsed_ms": round((perf_counter() - started_at) * 1000)}),
            )

        source_url = _extract_url(value)
        source_video_id = _extract_video_id(source_url)
        await report(
            ProcessingTraceStep(
                key="input_inspected",
                title="看懂了输入",
                detail=(
                    f"这是一个直接视频链接，视频 ID 是 {source_video_id}。"
                    if source_video_id
                    else "输入中包含抖音链接，我会先跟随公开跳转确认视频身份。"
                ),
                kind=ProcessingStepKind.OBSERVATION,
                data={
                    "input_type": "direct_url" if value.strip() == source_url else "share_text",
                    "video_id": source_video_id,
                },
            ),
        )
        await report(
            ProcessingTraceStep(
                key="target_validation",
                title="检查链接是否可以安全访问",
                detail="正在执行协议、域名、端口和公网地址安全校验。",
                kind=ProcessingStepKind.TOOL,
                status=ProcessingStepStatus.RUNNING,
            )
        )
        await _ensure_safe_url(source_url, self._resolver)
        await report(
            ProcessingTraceStep(
                key="target_validation",
                title="链接安全校验通过",
                detail="协议、抖音域名和公网解析地址均符合访问规则。",
                kind=ProcessingStepKind.TOOL,
            ),
        )
        used_detail_api = False
        await report(
            ProcessingTraceStep(
                key="share_page_fetch",
                title="读取抖音公开页面",
                detail="正在请求公开分享页，并查找页面中的作品状态。",
                kind=ProcessingStepKind.TOOL,
                status=ProcessingStepStatus.RUNNING,
            )
        )
        try:
            final_url, html = await self._fetch_page(source_url)
            parsed = self._douyin_parser.parse(
                html,
                source_url=source_url,
                final_url=final_url,
            )
        except (ContentUnavailableError, UpstreamFetchError):
            if not source_video_id:
                raise
            await report(
                ProcessingTraceStep(
                    key="share_page_fetch",
                    title="公开页面信息不足",
                    detail="公开分享页没有找到完整作品状态，不能据此继续分析。",
                    kind=ProcessingStepKind.WARNING,
                    status=ProcessingStepStatus.WARNING,
                    data={"reason": "incomplete_public_state"},
                )
            )
            await report(
                ProcessingTraceStep(
                    key="fallback_decision",
                    title="改用公开视频详情接口",
                    detail=(
                        f"链接已经提供视频 ID {source_video_id}，"
                        "可以在不使用登录 Cookie 的前提下查询公开详情。"
                    ),
                    kind=ProcessingStepKind.DECISION,
                    data={"video_id": source_video_id, "strategy": "public_detail_api"},
                )
            )
            await report(
                ProcessingTraceStep(
                    key="detail_api_fetch",
                    title="查询公开视频详情",
                    detail=f"正在读取视频 {source_video_id} 的公开详情数据。",
                    kind=ProcessingStepKind.TOOL,
                    status=ProcessingStepStatus.RUNNING,
                    data={"video_id": source_video_id},
                )
            )
            detail = await self._douyin_detail_client.get_video_detail(source_video_id)
            if not detail:
                await report(
                    ProcessingTraceStep(
                        key="detail_api_fetch",
                        title="公开视频详情不可用",
                        detail="详情接口没有返回可用作品数据。",
                        kind=ProcessingStepKind.WARNING,
                        status=ProcessingStepStatus.WARNING,
                        data={"video_id": source_video_id},
                    )
                )
                raise ContentUnavailableError(
                    "没有找到可用的视频内容，链接可能已失效或不是公开视频。"
                ) from None
            parsed = self._douyin_parser.parse_detail(
                detail,
                source_url=source_url,
                video_id=source_video_id,
            )
            used_detail_api = True
            await report(
                ProcessingTraceStep(
                    key="detail_api_fetch",
                    title="取得公开视频详情",
                    detail=f"详情接口返回了视频 {source_video_id} 的作品数据。",
                    kind=ProcessingStepKind.TOOL,
                    data={"video_id": source_video_id},
                )
            )
        content = parsed.content
        if not used_detail_api:
            await report(
                ProcessingTraceStep(
                    key="share_page_fetch",
                    title="取得公开视频数据",
                    detail="已读取公开分享页，并在页面状态中找到作品数据。",
                    kind=ProcessingStepKind.TOOL,
                    data={
                        "source": "public_share_page",
                        "video_id": content.video_id,
                    },
                ),
            )
        await report(
            ProcessingTraceStep(
                key="metadata_inspected",
                title="核对视频信息",
                detail=(
                    f"识别到作者 {content.author.name or '未知作者'}，"
                    f"视频时长 {content.duration_seconds:g} 秒。"
                    if content.duration_seconds is not None
                    else f"识别到作者 {content.author.name or '未知作者'}，视频时长未知。"
                ),
                kind=ProcessingStepKind.OBSERVATION,
                data={
                    "video_id": content.video_id,
                    "title": content.title,
                    "author": content.author.name,
                    "duration_seconds": content.duration_seconds,
                },
            ),
        )
        await report(
            ProcessingTraceStep(
                key="result_ready",
                title="公开视频信息已经整理好",
                detail="标题、作者、封面、时长和本地播放入口已经归一化。",
                kind=ProcessingStepKind.RESULT,
            ),
        )
        if content.video_id and parsed.playback_source_url:
            self._playback_sources[content.video_id] = parsed.playback_source_url
        if self._video_analyzer and content.video_id and parsed.playback_source_url:
            try:
                await report(
                    ProcessingTraceStep(
                        key="media_fetch",
                        title="读取视频媒体",
                        detail="正在沿安全播放链路读取完整视频，供语音转写使用。",
                        kind=ProcessingStepKind.TOOL,
                        status=ProcessingStepStatus.RUNNING,
                        data={"video_id": content.video_id},
                    ),
                )
                media_response = await self.fetch_playback(
                    content.video_id,
                    on_progress=report,
                )
                await report(
                    ProcessingTraceStep(
                        key="media_fetch",
                        title="视频媒体读取完成",
                        detail=f"已取得 {len(media_response.content):,} 字节视频数据。",
                        kind=ProcessingStepKind.TOOL,
                        data={
                            "video_id": content.video_id,
                            "byte_size": len(media_response.content),
                        },
                    ),
                )
                analysis = await self._video_analyzer.analyze(
                    video_id=content.video_id,
                    title=content.title,
                    video_content=media_response.content,
                    on_progress=lambda step: _report_progress(
                        completed_steps,
                        on_progress,
                        step.model_copy(
                            update={"elapsed_ms": round((perf_counter() - started_at) * 1000)}
                        ),
                    ),
                )
                content = content.model_copy(
                    update={
                        "status": ExtractionStatus.ANALYZED,
                        "transcript": analysis.transcript,
                        "coach_interpretation": analysis.interpretation,
                        "warnings": [
                            warning for warning in content.warnings if "字幕轨道" not in warning
                        ],
                    }
                )
            except (VideoAnalysisError, UnsafeVideoUrlError, UpstreamFetchError) as error:
                for pending_step in list(completed_steps):
                    if pending_step.status == ProcessingStepStatus.RUNNING:
                        await report(
                            pending_step.model_copy(
                                update={
                                    "title": f"{pending_step.title}未完成",
                                    "detail": f"该步骤已经停止：{error}",
                                    "kind": ProcessingStepKind.WARNING,
                                    "status": ProcessingStepStatus.WARNING,
                                }
                            )
                        )
                await report(
                    ProcessingTraceStep(
                        key="analysis_unavailable",
                        title="本次内容解读无法完成",
                        detail=f"已保留公开视频信息；未生成内容总结，因为：{error}",
                        kind=ProcessingStepKind.WARNING,
                        status=ProcessingStepStatus.WARNING,
                        data={"reason": str(error)},
                    )
                )
                content = content.model_copy(
                    update={"warnings": [*content.warnings, f"视频内容解读未完成：{error}"]}
                )
        return content.model_copy(update={"processing_trace": completed_steps})

    async def fetch_playback(
        self,
        video_id: str,
        *,
        range_header: str | None = None,
        on_progress: ProgressReporter | None = None,
    ) -> httpx.Response:
        source_url = self._playback_sources.get(video_id)
        if not source_url:
            raise ContentUnavailableError("视频播放地址已失效，请重新解析该视频。")

        headers = {
            "Accept": "video/mp4,video/*;q=0.9,*/*;q=0.5",
            "Referer": "https://www.douyin.com/",
            "User-Agent": _MOBILE_USER_AGENT,
        }
        if range_header and re.fullmatch(r"bytes=\d*-\d*", range_header):
            headers["Range"] = range_header

        async def notify(step: ProcessingTraceStep) -> None:
            if on_progress is None:
                return
            reported = on_progress(step)
            if isawaitable(reported):
                await reported

        for source_attempt in range(_MAX_MEDIA_SOURCE_ATTEMPTS):
            try:
                attempt_url = _media_source_for_attempt(source_url, source_attempt)
                response = await self._fetch_playback_source(attempt_url, headers=headers)
                await notify(
                    ProcessingTraceStep(
                        key="media_source_selected",
                        title="媒体线路可以使用",
                        detail=(
                            f"线路 {source_attempt} 通过安全校验，"
                            f"取得 {len(response.content):,} 字节视频数据。"
                        ),
                        kind=ProcessingStepKind.RESULT,
                        data={
                            "line": source_attempt,
                            "byte_size": len(response.content),
                        },
                    )
                )
                return response
            except (UnsafeVideoUrlError, UpstreamFetchError):
                if source_attempt == _MAX_MEDIA_SOURCE_ATTEMPTS - 1:
                    raise
                await notify(
                    ProcessingTraceStep(
                        key=f"media_line_retry_{source_attempt + 1}",
                        title="当前媒体线路不可用",
                        detail=(
                            f"线路 {source_attempt} 未通过安全或可用性检查，"
                            f"切换到线路 {source_attempt + 1}。"
                        ),
                        kind=ProcessingStepKind.WARNING,
                        status=ProcessingStepStatus.WARNING,
                        data={
                            "failed_line": source_attempt,
                            "next_line": source_attempt + 1,
                        },
                    )
                )

        raise UpstreamFetchError("视频平台暂时无法返回播放内容，请稍后重试。")

    async def _fetch_playback_source(
        self,
        source_url: str,
        *,
        headers: dict[str, str],
    ) -> httpx.Response:
        current_url = source_url
        for redirect_count in range(self._max_redirects + 1):
            await _ensure_safe_media_url(
                current_url,
                self._resolver,
                require_allowlisted_host=redirect_count == 0,
            )
            try:
                response = await self._fetcher.get(current_url, headers=headers)
            except httpx.TimeoutException as error:
                raise UpstreamFetchError("视频加载超时，请稍后重试。") from error
            except httpx.HTTPError as error:
                raise UpstreamFetchError("无法加载视频内容，请稍后重试。") from error

            if response.is_redirect:
                location = response.headers.get("location")
                if not location or redirect_count >= self._max_redirects:
                    raise UpstreamFetchError("视频播放地址跳转次数过多。")
                current_url = urljoin(current_url, location)
                continue

            if response.status_code not in {200, 206}:
                raise UpstreamFetchError("视频平台暂时无法返回播放内容，请稍后重试。")
            content_type = response.headers.get("content-type", "")
            if not (
                content_type.lower().startswith("video/")
                or content_type.lower().startswith("application/octet-stream")
            ):
                raise UpstreamFetchError("视频平台返回了不支持的播放格式。")

            return response

        raise UpstreamFetchError("视频播放地址跳转次数过多。")

    async def _fetch_page(self, source_url: str) -> tuple[str, str]:
        current_url = source_url
        canonical_url = source_url
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
            "User-Agent": _USER_AGENT,
        }

        for redirect_count in range(self._max_redirects + 1):
            await _ensure_safe_url(current_url, self._resolver)

            video_id = _extract_video_id(current_url)
            is_public_share_page = "iesdouyin.com/share/video/" in current_url
            if video_id and not is_public_share_page:
                canonical_url = f"https://www.douyin.com/video/{video_id}"
                current_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
                await _ensure_safe_url(current_url, self._resolver)
                headers = {**headers, "User-Agent": _MOBILE_USER_AGENT}

            try:
                response = await self._fetcher.get(current_url, headers=headers)
            except httpx.TimeoutException as error:
                raise UpstreamFetchError("视频平台响应超时，请稍后重试。") from error
            except httpx.HTTPError as error:
                raise UpstreamFetchError("无法连接视频平台，请稍后重试。") from error

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise UpstreamFetchError("视频平台返回了无效的跳转地址。")
                if redirect_count >= self._max_redirects:
                    raise UpstreamFetchError("视频链接跳转次数过多。")
                current_url = urljoin(current_url, location)
                continue

            if response.status_code >= 400:
                raise UpstreamFetchError("视频平台暂时无法返回该内容，请稍后重试。")
            if len(response.content) > self._max_response_bytes:
                raise UpstreamFetchError("视频页面响应过大，已停止处理。")

            content_type = response.headers.get("content-type", "text/html")
            if "html" not in content_type.lower():
                raise UpstreamFetchError("视频平台返回了不支持的内容格式。")
            final_url = canonical_url if video_id else str(response.url)
            return final_url, response.text

        raise UpstreamFetchError("视频链接跳转次数过多。")
