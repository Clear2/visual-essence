from pathlib import Path

import pytest

from app.conversations.store import FileConversationStore


@pytest.mark.asyncio
async def test_file_conversation_store_persists_the_source_behind_an_opaque_id(
    tmp_path: Path,
) -> None:
    first_store = FileConversationStore(tmp_path)
    conversation = await first_store.create("https://www.douyin.com/video/7670495404269604134")

    restored = await FileConversationStore(tmp_path).get(conversation.id)

    assert restored == conversation
    assert conversation.id != conversation.source_url
    assert "/" not in conversation.id


@pytest.mark.asyncio
async def test_file_conversation_store_rejects_a_non_uuid_lookup(tmp_path: Path) -> None:
    store = FileConversationStore(tmp_path)

    assert await store.get("https://www.douyin.com/video/1") is None
