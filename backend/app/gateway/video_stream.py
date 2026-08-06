from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from inspect import isawaitable
from typing import Any

from fastapi.responses import StreamingResponse

from app.videos.errors import (
    ContentUnavailableError,
    UnsafeVideoUrlError,
    UnsupportedPlatformError,
    UpstreamFetchError,
    VideoExtractionError,
)
from app.videos.extractor import VideoExtractionModule

ResultReporter = Callable[[dict[str, Any]], object]


def _public_error_message(error: Exception) -> str:
    if isinstance(
        error,
        (
            UnsupportedPlatformError,
            UnsafeVideoUrlError,
            ContentUnavailableError,
            UpstreamFetchError,
        ),
    ):
        return str(error)
    return "视频内容解析失败，请稍后重试。"


def _ndjson(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def stream_video_extraction(
    extractor: VideoExtractionModule,
    source_url: str,
    *,
    on_result: ResultReporter | None = None,
) -> StreamingResponse:
    async def events() -> AsyncIterator[bytes]:
        queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

        async def report_progress(step: object) -> None:
            model_dump = step.model_dump
            await queue.put({"type": "progress", "step": model_dump(mode="json")})

        async def run_extraction() -> None:
            try:
                await queue.put({"type": "conversation", "source_url": source_url})
                result = await extractor.extract(source_url, on_progress=report_progress)
            except VideoExtractionError as error:
                await queue.put({"type": "error", "message": _public_error_message(error)})
            except Exception:
                await queue.put({"type": "error", "message": "视频内容解析失败，请稍后重试。"})
            else:
                video = result.model_dump(mode="json")
                if on_result is not None:
                    reported = on_result(video)
                    if isawaitable(reported):
                        await reported
                await queue.put({"type": "result", "video": video})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_extraction())
        try:
            while (event := await queue.get()) is not None:
                yield _ndjson(event)
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
