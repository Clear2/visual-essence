from fastapi import Request

from app.conversations.coach import ConversationCoach
from app.conversations.store import ConversationStore
from app.videos.extractor import VideoExtractionModule


def get_video_extractor(request: Request) -> VideoExtractionModule:
    """Return the application-owned video extraction module."""

    return request.app.state.video_extractor


def get_conversation_store(request: Request) -> ConversationStore:
    return request.app.state.conversation_store


def get_conversation_coach(request: Request) -> ConversationCoach | None:
    return request.app.state.conversation_coach
