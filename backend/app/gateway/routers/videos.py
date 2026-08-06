from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from fastapi.responses import StreamingResponse

from app.gateway.deps import get_video_extractor
from app.gateway.video_stream import stream_video_extraction
from app.videos.contracts import ExtractVideoRequest, VideoContentResponse
from app.videos.errors import (
    ContentUnavailableError,
    UnsafeVideoUrlError,
    UnsupportedPlatformError,
    UpstreamFetchError,
    VideoExtractionError,
)
from app.videos.extractor import VideoExtractionModule

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get(
    "/{video_id}/playback",
    summary="Play an extracted public video",
    description="Proxy verified video bytes without exposing signed upstream URLs.",
)
async def playback_video(
    request: Request,
    video_id: Annotated[str, Path(pattern=r"^\d{6,32}$")],
    extractor: Annotated[VideoExtractionModule, Depends(get_video_extractor)],
) -> Response:
    try:
        upstream = await extractor.fetch_playback(
            video_id,
            range_header=request.headers.get("range"),
        )
    except ContentUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (UnsafeVideoUrlError, UpstreamFetchError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    forwarded_headers = {
        name: value
        for name in ("content-type", "content-length", "content-range", "accept-ranges")
        if (value := upstream.headers.get(name)) is not None
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=forwarded_headers,
    )


@router.post(
    "/extract",
    response_model=VideoContentResponse,
    summary="Extract public video content",
    description="Resolve a public share URL and return normalized video metadata.",
)
async def extract_video(
    body: ExtractVideoRequest,
    extractor: Annotated[VideoExtractionModule, Depends(get_video_extractor)],
) -> VideoContentResponse:
    try:
        return await extractor.extract(body.url)
    except (UnsupportedPlatformError, UnsafeVideoUrlError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except ContentUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except UpstreamFetchError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except VideoExtractionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="视频内容解析失败，请稍后重试。",
        ) from error


@router.post(
    "/extract/stream",
    summary="Stream public video extraction progress",
    description="Stream observable extraction stages followed by the normalized result.",
)
async def stream_extract_video(
    body: ExtractVideoRequest,
    extractor: Annotated[VideoExtractionModule, Depends(get_video_extractor)],
) -> StreamingResponse:
    return stream_video_extraction(extractor, body.url)
