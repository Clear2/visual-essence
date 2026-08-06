from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.conversations.coach import ConversationCoach, ConversationNotReadyError
from app.conversations.store import ConversationMessage, ConversationStore
from app.gateway.deps import (
    get_conversation_coach,
    get_conversation_store,
    get_video_extractor,
)
from app.gateway.video_stream import stream_video_extraction
from app.videos.contracts import ExtractVideoRequest, VideoContentResponse
from app.videos.errors import VideoAnalysisError
from app.videos.extractor import VideoExtractionModule

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class CreateConversationResponse(BaseModel):
    id: str = Field(pattern=r"^[0-9a-f-]{36}$")


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    video: VideoContentResponse | None
    messages: list[ConversationMessageResponse]


class CreateMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CreateMessageResponse(BaseModel):
    message: ConversationMessageResponse


@router.post("", response_model=CreateConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ExtractVideoRequest,
    store: Annotated[ConversationStore, Depends(get_conversation_store)],
) -> CreateConversationResponse:
    conversation = await store.create(body.url)
    return CreateConversationResponse(id=conversation.id)


@router.post(
    "/{conversation_id}/extract/stream",
    summary="Stream extraction inside a persisted video conversation",
)
async def stream_conversation_extraction(
    conversation_id: Annotated[
        str,
        Path(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    ],
    store: Annotated[ConversationStore, Depends(get_conversation_store)],
    extractor: Annotated[VideoExtractionModule, Depends(get_video_extractor)],
) -> StreamingResponse:
    conversation = await store.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在或已失效。")
    return stream_video_extraction(
        extractor,
        conversation.source_url,
        on_result=lambda video: store.save_video(conversation_id, video),
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: Annotated[
        str,
        Path(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    ],
    store: Annotated[ConversationStore, Depends(get_conversation_store)],
) -> ConversationResponse:
    conversation = await store.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在或已失效。")
    return ConversationResponse(
        id=conversation.id,
        video=(
            VideoContentResponse.model_validate(conversation.video)
            if conversation.video is not None
            else None
        ),
        messages=[
            ConversationMessageResponse.model_validate(item) for item in conversation.messages
        ],
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=CreateMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation_message(
    conversation_id: Annotated[
        str,
        Path(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    ],
    body: CreateMessageRequest,
    store: Annotated[ConversationStore, Depends(get_conversation_store)],
    coach: Annotated[ConversationCoach | None, Depends(get_conversation_coach)],
) -> CreateMessageResponse:
    conversation = await store.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在或已失效。")
    if coach is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 视频私教尚未配置。",
        )
    try:
        answer = await coach.answer(conversation, body.content.strip())
    except ConversationNotReadyError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except VideoAnalysisError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    assistant_message: ConversationMessage = await store.append_exchange(
        conversation_id,
        body.content.strip(),
        answer,
    )
    return CreateMessageResponse(
        message=ConversationMessageResponse.model_validate(assistant_message)
    )
