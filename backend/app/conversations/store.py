from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

_CONVERSATION_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    id: str
    role: str
    content: str
    created_at: str


@dataclass(frozen=True, slots=True)
class VideoConversation:
    id: str
    source_url: str
    created_at: str = ""
    video: dict[str, Any] | None = None
    messages: tuple[ConversationMessage, ...] = ()


class ConversationStore(Protocol):
    async def create(self, source_url: str) -> VideoConversation: ...

    async def get(self, conversation_id: str) -> VideoConversation | None: ...

    async def save_video(self, conversation_id: str, video: dict[str, Any]) -> None: ...

    async def append_exchange(
        self,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
    ) -> ConversationMessage: ...


class FileConversationStore:
    """Persist small conversation records without exposing source URLs in routes."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._lock = asyncio.Lock()

    async def create(self, source_url: str) -> VideoConversation:
        conversation = VideoConversation(
            id=str(uuid4()),
            source_url=source_url,
            created_at=datetime.now(UTC).isoformat(),
        )
        async with self._lock:
            await asyncio.to_thread(self._write, conversation)
        return conversation

    async def get(self, conversation_id: str) -> VideoConversation | None:
        normalized = conversation_id.strip().lower()
        if not _CONVERSATION_ID_PATTERN.fullmatch(normalized):
            return None
        return await asyncio.to_thread(self._read, normalized)

    async def save_video(self, conversation_id: str, video: dict[str, Any]) -> None:
        async with self._lock:
            conversation = await asyncio.to_thread(self._read, conversation_id)
            if conversation is None:
                return
            await asyncio.to_thread(
                self._write,
                VideoConversation(
                    id=conversation.id,
                    source_url=conversation.source_url,
                    created_at=conversation.created_at,
                    video=video,
                    messages=conversation.messages,
                ),
            )

    async def append_exchange(
        self,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
    ) -> ConversationMessage:
        timestamp = datetime.now(UTC).isoformat()
        user_message = ConversationMessage(
            id=str(uuid4()),
            role="user",
            content=user_content,
            created_at=timestamp,
        )
        assistant_message = ConversationMessage(
            id=str(uuid4()),
            role="assistant",
            content=assistant_content,
            created_at=datetime.now(UTC).isoformat(),
        )
        async with self._lock:
            conversation = await asyncio.to_thread(self._read, conversation_id)
            if conversation is None:
                raise LookupError("Conversation not found")
            await asyncio.to_thread(
                self._write,
                VideoConversation(
                    id=conversation.id,
                    source_url=conversation.source_url,
                    created_at=conversation.created_at,
                    video=conversation.video,
                    messages=(
                        *conversation.messages,
                        user_message,
                        assistant_message,
                    ),
                ),
            )
        return assistant_message

    def _write(self, conversation: VideoConversation) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        target = self._directory / f"{conversation.id}.json"
        temporary = self._directory / f".{conversation.id}.tmp"
        temporary.write_text(
            json.dumps(asdict(conversation), ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(target)

    def _read(self, conversation_id: str) -> VideoConversation | None:
        path = self._directory / f"{conversation_id}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        try:
            return VideoConversation(
                id=str(payload["id"]),
                source_url=str(payload["source_url"]),
                created_at=str(payload.get("created_at") or ""),
                video=payload.get("video") if isinstance(payload.get("video"), dict) else None,
                messages=tuple(
                    ConversationMessage(
                        id=str(message["id"]),
                        role=str(message["role"]),
                        content=str(message["content"]),
                        created_at=str(message["created_at"]),
                    )
                    for message in payload.get("messages", [])
                    if isinstance(message, dict)
                    and all(key in message for key in ("id", "role", "content", "created_at"))
                ),
            )
        except KeyError:
            return None
