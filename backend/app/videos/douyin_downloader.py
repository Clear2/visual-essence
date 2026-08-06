from __future__ import annotations

from typing import Any, Protocol

from app.videos.errors import UpstreamFetchError


class DouyinDetailClient(Protocol):
    async def get_video_detail(self, video_id: str) -> dict[str, Any] | None: ...


class DouyinDownloaderDetailClient:
    """Small adapter around jiji262/douyin-downloader's public detail client."""

    async def get_video_detail(self, video_id: str) -> dict[str, Any] | None:
        try:
            from core.api_client import DouyinAPIClient
        except ImportError as error:
            raise UpstreamFetchError("抖音详情提取组件尚未安装。") from error

        try:
            async with DouyinAPIClient(cookies={}) as client:
                return await client.get_video_detail(video_id, suppress_error=True)
        except Exception as error:
            raise UpstreamFetchError("无法读取抖音公开视频详情，请稍后重试。") from error
