from __future__ import annotations

import json
from urllib.parse import quote

import httpx
import pytest

from app.videos.analysis import VideoAnalysisResult, VideoAnalyzer
from app.videos.contracts import ProcessingTraceStep, VideoCoachInterpretation
from app.videos.errors import UnsafeVideoUrlError, UnsupportedPlatformError, VideoAnalysisError
from app.videos.extractor import VideoExtractionModule


async def public_resolver(_hostname: str) -> set[str]:
    return {"1.1.1.1"}


def douyin_html() -> str:
    state = {
        "app": {
            "aweme_detail": {
                "aweme_id": "7420000000000000000",
                "desc": "把一条视频变成可以阅读的内容",
                "author": {
                    "nickname": "Visual Creator",
                    "avatar_thumb": {"url_list": ["https://example.com/avatar.jpg"]},
                },
                "video": {
                    "duration": 15420,
                    "cover": {"url_list": ["https://example.com/cover.jpg"]},
                    "play_addr": {
                        "url_list": ["https://v3-web.douyinvod.com/video/tos/example-playback"]
                    },
                },
            }
        }
    }
    return f"""
    <html><head>
      <meta property="og:url" content="https://www.douyin.com/video/7420000000000000000" />
      <meta property="og:description" content="公开视频简介" />
    </head><body>
      <script id="RENDER_DATA" type="application/json">{quote(json.dumps(state))}</script>
    </body></html>
    """


class FakeDouyinDetailClient:
    def __init__(self, detail: dict[str, object]) -> None:
        self.detail = detail
        self.requested_video_ids: list[str] = []

    async def get_video_detail(self, video_id: str) -> dict[str, object]:
        self.requested_video_ids.append(video_id)
        return self.detail


class FakeVideoAnalyzer(VideoAnalyzer):
    def __init__(self) -> None:
        self.analyzed: list[tuple[str, str, bytes]] = []

    async def analyze(
        self,
        *,
        video_id: str,
        title: str,
        video_content: bytes,
        on_progress=None,
    ) -> VideoAnalysisResult:
        self.analyzed.append((video_id, title, video_content))
        if on_progress:
            await on_progress(
                ProcessingTraceStep(
                    key="audio_transcribed",
                    title="转写视频语音",
                    detail="已从视频音轨中识别出口播文本。",
                )
            )
            await on_progress(
                ProcessingTraceStep(
                    key="content_interpreted",
                    title="生成内容解读",
                    detail="语言模型已依据转写文本生成结构化总结。",
                )
            )
        return VideoAnalysisResult(
            transcript="北魏先后出现十一位皇帝，视频逐一梳理了他们的继位与改革。",
            interpretation=VideoCoachInterpretation(
                summary="视频按时间顺序梳理北魏十一位皇帝，重点讨论政权更替与孝文帝改革。",
                key_points=[
                    "北魏皇位传承多次受到权臣与宗室斗争影响。",
                    "孝文帝改革推动迁都洛阳与汉化政策。",
                    "理解人物关系要结合继位顺序与政治背景。",
                ],
                questions=["孝文帝改革为什么同时带来整合与冲突？"],
            ),
        )


class FailingVideoAnalyzer(VideoAnalyzer):
    async def analyze(
        self,
        *,
        video_id: str,
        title: str,
        video_content: bytes,
        on_progress=None,
    ) -> VideoAnalysisResult:
        raise VideoAnalysisError("没有从视频音轨中识别出可用文本。")


@pytest.mark.asyncio
async def test_extract_returns_transcript_and_llm_interpretation_when_analysis_succeeds() -> None:
    analyzer = FakeVideoAnalyzer()
    reported_steps = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "v3-web.douyinvod.com":
            return httpx.Response(
                200,
                content=b"complete-video-content",
                headers={"content-type": "video/mp4"},
                request=request,
            )
        return httpx.Response(
            200,
            text=douyin_html(),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(
            client,
            resolver=public_resolver,
            video_analyzer=analyzer,
        )
        result = await extractor.extract(
            "https://www.douyin.com/video/7420000000000000000",
            on_progress=reported_steps.append,
        )

    assert analyzer.analyzed == [
        (
            "7420000000000000000",
            "把一条视频变成可以阅读的内容",
            b"complete-video-content",
        )
    ]
    assert result.status == "analyzed"
    assert result.transcript == "北魏先后出现十一位皇帝，视频逐一梳理了他们的继位与改革。"
    assert result.coach_interpretation is not None
    assert result.coach_interpretation.summary.startswith("视频按时间顺序梳理")
    assert result.coach_interpretation.key_points[1] == "孝文帝改革推动迁都洛阳与汉化政策。"
    metadata_event = next(
        step for step in result.processing_trace if step.key == "metadata_inspected"
    )
    assert metadata_event.kind == "observation"
    assert metadata_event.data == {
        "video_id": "7420000000000000000",
        "title": "把一条视频变成可以阅读的内容",
        "author": "Visual Creator",
        "duration_seconds": 15.42,
    }
    assert "Visual Creator" in metadata_event.detail
    assert "15.42 秒" in metadata_event.detail
    media_events = [step for step in reported_steps if step.key == "media_fetch"]
    assert [step.status for step in media_events] == ["running", "complete"]
    assert media_events[-1].data == {"video_id": "7420000000000000000", "byte_size": 22}
    assert [step.key for step in result.processing_trace][-2:] == [
        "audio_transcribed",
        "content_interpreted",
    ]
    latest_report_by_key = {step.key: step for step in reported_steps}
    assert [latest_report_by_key[step.key] for step in result.processing_trace] == list(
        result.processing_trace
    )
    assert all("字幕轨道" not in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_extract_keeps_metadata_without_fabricating_summary_when_analysis_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "v3-web.douyinvod.com":
            return httpx.Response(
                200,
                content=b"video-without-recognizable-speech",
                headers={"content-type": "video/mp4"},
                request=request,
            )
        return httpx.Response(
            200,
            text=douyin_html(),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(
            client,
            resolver=public_resolver,
            video_analyzer=FailingVideoAnalyzer(),
        )
        result = await extractor.extract("https://www.douyin.com/video/7420000000000000000")

    assert result.status == "metadata"
    assert result.title == "把一条视频变成可以阅读的内容"
    assert result.transcript is None
    assert result.coach_interpretation is None
    assert result.warnings[-1] == ("视频内容解读未完成：没有从视频音轨中识别出可用文本。")
    failure_event = next(
        step for step in result.processing_trace if step.key == "analysis_unavailable"
    )
    assert failure_event.kind == "warning"
    assert failure_event.status == "warning"
    assert "没有从视频音轨中识别出可用文本" in failure_event.detail
    assert all(step.status != "running" for step in result.processing_trace)
    assert [step.key for step in result.processing_trace] == [
        "input_inspected",
        "target_validation",
        "share_page_fetch",
        "metadata_inspected",
        "result_ready",
        "media_fetch",
        "media_source_selected",
        "analysis_unavailable",
    ]


@pytest.mark.asyncio
async def test_extract_uses_douyin_downloader_for_a_jingxuan_modal_link() -> None:
    video_id = "7667128493197192313"
    requested_urls: list[str] = []
    reported_steps: list[ProcessingTraceStep] = []
    detail_client = FakeDouyinDetailClient(
        {
            "aweme_id": video_id,
            "desc": "精选页面中的公开视频",
            "author": {"nickname": "公开视频作者"},
            "video": {
                "duration": 19970,
                "cover": {"url_list": ["https://example.com/jingxuan-cover.jpg"]},
                "bit_rate": [
                    {
                        "bit_rate": 800_000,
                        "play_addr": {
                            "width": 720,
                            "height": 1280,
                            "url_list": ["https://v3-web.douyinvod.com/video/720p-playback"],
                        },
                    },
                    {
                        "bit_rate": 1_600_000,
                        "play_addr": {
                            "width": 1080,
                            "height": 1920,
                            "url_list": ["https://v9-web.douyinvod.com/video/1080p-playback"],
                        },
                    },
                ],
            },
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(
            200,
            text="<html><body>精选频道页面，没有作品详情状态</body></html>",
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(
            client,
            resolver=public_resolver,
            douyin_detail_client=detail_client,
        )
        result = await extractor.extract(
            f"https://www.douyin.com/jingxuan?modal_id={video_id}",
            on_progress=reported_steps.append,
        )

    assert requested_urls == [f"https://www.iesdouyin.com/share/video/{video_id}/"]
    assert detail_client.requested_video_ids == [video_id]
    assert result.video_id == video_id
    assert result.canonical_url == f"https://www.douyin.com/video/{video_id}"
    assert result.title == "精选页面中的公开视频"
    assert result.author.name == "公开视频作者"
    assert result.duration_seconds == 19.97
    assert result.playback_url == f"/api/videos/{video_id}/playback"
    assert "douyinvod.com" not in result.model_dump_json()
    share_page_events = [step for step in reported_steps if step.key == "share_page_fetch"]
    assert [step.status for step in share_page_events] == ["running", "warning"]
    assert "没有找到完整作品状态" in share_page_events[-1].detail
    assert next(step for step in reported_steps if step.key == "fallback_decision").kind == (
        "decision"
    )
    detail_events = [step for step in reported_steps if step.key == "detail_api_fetch"]
    assert [step.status for step in detail_events] == ["running", "complete"]
    assert detail_events[-1].data["video_id"] == video_id


@pytest.mark.asyncio
async def test_extract_resolves_short_link_and_normalizes_metadata() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.host == "v.douyin.com":
            return httpx.Response(
                302,
                headers={"location": "https://www.douyin.com/video/7420000000000000000"},
                request=request,
            )
        return httpx.Response(
            200,
            text=douyin_html(),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(client, resolver=public_resolver)
        result = await extractor.extract("复制打开抖音 https://v.douyin.com/example/ 看视频")

    assert calls == [
        "https://v.douyin.com/example/",
        "https://www.iesdouyin.com/share/video/7420000000000000000/",
    ]
    assert result.video_id == "7420000000000000000"
    assert result.title == "把一条视频变成可以阅读的内容"
    assert result.author.name == "Visual Creator"
    assert result.duration_seconds == 15.42
    assert result.playback_url == "/api/videos/7420000000000000000/playback"
    assert "douyinvod.com" not in result.model_dump_json()
    assert result.transcript is None
    assert [step.key for step in result.processing_trace] == [
        "input_inspected",
        "target_validation",
        "share_page_fetch",
        "metadata_inspected",
        "result_ready",
    ]
    assert all(step.status == "complete" for step in result.processing_trace)
    assert result.processing_trace[-1].detail == (
        "标题、作者、封面、时长和本地播放入口已经归一化。"
    )


@pytest.mark.asyncio
async def test_extract_streams_running_and_completed_public_activity() -> None:
    reported_steps: list[ProcessingTraceStep] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=douyin_html(),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(client, resolver=public_resolver)
        result = await extractor.extract(
            "https://www.douyin.com/video/7420000000000000000",
            on_progress=reported_steps.append,
        )

    target_events = [step for step in reported_steps if step.key == "target_validation"]
    assert [step.status for step in target_events] == ["running", "complete"]
    assert target_events[0].kind == "tool"
    assert "安全校验" in target_events[0].detail

    page_events = [step for step in reported_steps if step.key == "share_page_fetch"]
    assert [step.status for step in page_events] == ["running", "complete"]
    assert page_events[-1].data["source"] == "public_share_page"

    assert [step.key for step in result.processing_trace] == [
        "input_inspected",
        "target_validation",
        "share_page_fetch",
        "metadata_inspected",
        "result_ready",
    ]
    assert all(step.status == "complete" for step in result.processing_trace)
    assert len({step.key for step in result.processing_trace}) == len(result.processing_trace)
    assert all(step.elapsed_ms >= 0 for step in reported_steps)


@pytest.mark.asyncio
async def test_fetch_playback_proxies_the_registered_media_source() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "v3-web.douyinvod.com":
            return httpx.Response(
                302,
                headers={"location": "https://v9-web.douyinvod.com/video/tos/example-playback"},
                request=request,
            )
        if request.url.host == "v9-web.douyinvod.com":
            return httpx.Response(
                206,
                content=b"video-bytes",
                headers={
                    "content-type": "video/mp4",
                    "content-range": "bytes 0-10/11",
                    "accept-ranges": "bytes",
                },
                request=request,
            )
        return httpx.Response(
            200,
            text=douyin_html(),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(client, resolver=public_resolver)
        await extractor.extract("https://www.douyin.com/video/7420000000000000000")
        response = await extractor.fetch_playback(
            "7420000000000000000",
            range_header="bytes=0-10",
        )

    assert response.content == b"video-bytes"
    playback_request = requests[-1]
    assert playback_request.url.host == "v9-web.douyinvod.com"
    assert playback_request.headers["range"] == "bytes=0-10"
    assert playback_request.headers["referer"] == "https://www.douyin.com/"


@pytest.mark.asyncio
async def test_fetch_playback_accepts_a_public_https_cdn_redirect_from_an_allowed_source() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "aweme.snssdk.com":
            assert request.url.path == "/aweme/v1/play/"
            assert request.url.params["watermark"] == "0"
            assert "logo_name" not in request.url.params
            return httpx.Response(
                302,
                headers={"location": "https://media.example-cdn.com/video/example"},
                request=request,
            )
        if request.url.host == "media.example-cdn.com":
            return httpx.Response(
                206,
                content=b"redirected-video-byte",
                headers={"content-type": "video/mp4"},
                request=request,
            )
        return httpx.Response(
            200,
            text=douyin_html().replace(
                quote("https://v3-web.douyinvod.com/video/tos/example-playback"),
                quote(
                    "https://aweme.snssdk.com/aweme/v1/playwm/?"
                    "video_id=example&ratio=720p&line=0&logo_name=douyin"
                ),
            ),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(client, resolver=public_resolver)
        await extractor.extract("https://www.douyin.com/video/7420000000000000000")
        response = await extractor.fetch_playback(
            "7420000000000000000",
            range_header="bytes=0-0",
        )

    assert response.content == b"redirected-video-byte"


@pytest.mark.asyncio
async def test_fetch_playback_rejects_a_private_cdn_redirect() -> None:
    async def resolver(hostname: str) -> set[str]:
        return {"127.0.0.1"} if hostname == "media.example-cdn.com" else {"1.1.1.1"}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "aweme.snssdk.com":
            return httpx.Response(
                302,
                headers={"location": "https://media.example-cdn.com/video/example"},
                request=request,
            )
        return httpx.Response(
            200,
            text=douyin_html().replace(
                quote("https://v3-web.douyinvod.com/video/tos/example-playback"),
                quote("https://aweme.snssdk.com/aweme/v1/play/example"),
            ),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(client, resolver=resolver)
        await extractor.extract("https://www.douyin.com/video/7420000000000000000")
        with pytest.raises(UnsafeVideoUrlError):
            await extractor.fetch_playback("7420000000000000000")


@pytest.mark.asyncio
async def test_fetch_playback_retries_the_allowed_source_after_an_unsafe_cdn_redirect() -> None:
    requested_lines: list[str] = []
    reported_steps: list[ProcessingTraceStep] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "aweme.snssdk.com":
            line = request.url.params["line"]
            requested_lines.append(line)
            location = (
                "https://untrusted.example-cdn.com:45678/video/example"
                if line == "0"
                else "https://media.example-cdn.com/video/example"
            )
            return httpx.Response(302, headers={"location": location}, request=request)
        if request.url.host == "media.example-cdn.com":
            return httpx.Response(
                206,
                content=b"healthy-video-byte",
                headers={"content-type": "video/mp4"},
                request=request,
            )
        return httpx.Response(
            200,
            text=douyin_html().replace(
                quote("https://v3-web.douyinvod.com/video/tos/example-playback"),
                quote(
                    "https://aweme.snssdk.com/aweme/v1/play/?"
                    "video_id=example&ratio=1080p&line=0&watermark=0"
                ),
            ),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(client, resolver=public_resolver)
        await extractor.extract("https://www.douyin.com/video/7420000000000000000")
        response = await extractor.fetch_playback(
            "7420000000000000000",
            on_progress=reported_steps.append,
        )

    assert requested_lines == ["0", "1"]
    assert response.content == b"healthy-video-byte"
    retry = next(step for step in reported_steps if step.key == "media_line_retry_1")
    assert retry.kind == "warning"
    assert retry.status == "warning"
    assert retry.data == {"failed_line": 0, "next_line": 1}
    assert "切换到线路 1" in retry.detail
    selected = next(step for step in reported_steps if step.key == "media_source_selected")
    assert selected.data == {"line": 1, "byte_size": 18}


@pytest.mark.asyncio
async def test_fetch_playback_uses_additional_bounded_lines_after_repeated_unsafe_redirects() -> (
    None
):
    requested_lines: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "aweme.snssdk.com":
            line = request.url.params["line"]
            requested_lines.append(line)
            location = (
                "https://media.example-cdn.com/video/example"
                if line == "4"
                else "https://untrusted.example-cdn.com:45678/video/example"
            )
            return httpx.Response(302, headers={"location": location}, request=request)
        if request.url.host == "media.example-cdn.com":
            return httpx.Response(
                200,
                content=b"healthy-video-after-more-lines",
                headers={"content-type": "video/mp4"},
                request=request,
            )
        return httpx.Response(
            200,
            text=douyin_html().replace(
                quote("https://v3-web.douyinvod.com/video/tos/example-playback"),
                quote(
                    "https://aweme.snssdk.com/aweme/v1/play/?"
                    "video_id=example&ratio=1080p&line=0&watermark=0"
                ),
            ),
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = VideoExtractionModule(client, resolver=public_resolver)
        await extractor.extract("https://www.douyin.com/video/7420000000000000000")
        response = await extractor.fetch_playback("7420000000000000000")

    assert requested_lines == ["0", "1", "2", "3", "4"]
    assert response.content == b"healthy-video-after-more-lines"


@pytest.mark.asyncio
async def test_extract_rejects_an_unsupported_platform_before_fetch() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: None)) as client:
        extractor = VideoExtractionModule(client, resolver=public_resolver)
        with pytest.raises(UnsupportedPlatformError):
            await extractor.extract("https://www.bilibili.com/video/BV1example")


@pytest.mark.asyncio
async def test_extract_rejects_a_private_dns_target() -> None:
    async def private_resolver(_hostname: str) -> set[str]:
        return {"127.0.0.1"}

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: None)) as client:
        extractor = VideoExtractionModule(client, resolver=private_resolver)
        with pytest.raises(UnsafeVideoUrlError):
            await extractor.extract("https://v.douyin.com/example/")
