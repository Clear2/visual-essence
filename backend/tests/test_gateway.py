import httpx
from fastapi.testclient import TestClient

from app.conversations.coach import TranscriptConversationCoach
from app.conversations.store import VideoConversation
from app.gateway.app import create_app
from app.gateway.config import GatewayConfig
from app.gateway.deps import (
    get_conversation_coach,
    get_conversation_store,
    get_video_extractor,
)
from app.videos.contracts import (
    ExtractionStatus,
    ProcessingTraceStep,
    VideoCoachInterpretation,
    VideoContentResponse,
    VideoPlatform,
)


class FakeVideoExtractor:
    async def extract(self, url: str, *, on_progress=None) -> VideoContentResponse:
        if on_progress:
            await on_progress(
                ProcessingTraceStep(
                    key="link_recognized",
                    title="识别视频链接",
                    detail="已识别链接。",
                )
            )
        return VideoContentResponse(
            platform=VideoPlatform.DOUYIN,
            status=ExtractionStatus.ANALYZED,
            source_url=url,
            canonical_url="https://www.douyin.com/video/7420000000000000000",
            video_id="7420000000000000000",
            title="测试视频",
            playback_url="/api/videos/7420000000000000000/playback",
            transcript="视频解释了 ask after 表示问候或打听某人的近况。",
            coach_interpretation=VideoCoachInterpretation(
                summary="视频讲解 ask after 的含义。",
                key_points=["ask after 表示问候或打听近况。"],
                questions=[],
            ),
        )

    async def fetch_playback(
        self, video_id: str, *, range_header: str | None = None
    ) -> httpx.Response:
        assert video_id == "7420000000000000000"
        assert range_header == "bytes=0-3"
        return httpx.Response(
            206,
            content=b"video",
            headers={
                "content-type": "video/mp4",
                "content-range": "bytes 0-4/5",
                "accept-ranges": "bytes",
            },
        )


class FakeConversationStore:
    def __init__(self) -> None:
        self.conversation = VideoConversation(
            id="0198c7a0-6f66-7c75-a318-acde48001122",
            source_url="https://www.douyin.com/video/7670495404269604134",
        )

    async def create(self, source_url: str) -> VideoConversation:
        return VideoConversation(id=self.conversation.id, source_url=source_url)

    async def get(self, conversation_id: str) -> VideoConversation | None:
        return self.conversation if conversation_id == self.conversation.id else None

    async def save_video(self, conversation_id: str, video: dict) -> None:
        return None


class FakeChatLlm:
    async def invoke(self, *, system_instruction: str, user_content: str) -> str:
        assert "只依据视频转写" in system_instruction
        assert "ask after" in user_content
        assert "这个短语是什么意思？" in user_content
        return "ask after 在这里表示问候某人，或打听某人的健康和近况。"


def test_health_check() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "visual-essence-api"}


def test_extract_video_uses_the_video_module_interface() -> None:
    app = create_app()
    app.dependency_overrides[get_video_extractor] = lambda: FakeVideoExtractor()

    with TestClient(app) as client:
        response = client.post(
            "/api/videos/extract",
            json={"url": "https://v.douyin.com/example/"},
        )

    assert response.status_code == 200
    assert response.json()["title"] == "测试视频"
    assert response.json()["platform"] == "douyin"


def test_extract_video_streams_verified_progress_before_the_result() -> None:
    app = create_app()
    app.dependency_overrides[get_video_extractor] = lambda: FakeVideoExtractor()

    with TestClient(app) as client:
        response = client.post(
            "/api/videos/extract/stream",
            json={"url": "https://v.douyin.com/example/"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = [line for line in response.text.splitlines() if line]
    assert '"type":"conversation"' in events[0]
    assert '"type":"progress"' in events[1]
    assert '"key":"link_recognized"' in events[1]
    assert '"type":"result"' in events[-1]
    assert '"title":"测试视频"' in events[-1]


def test_create_conversation_returns_an_opaque_id_and_streams_by_that_id() -> None:
    app = create_app()
    store = FakeConversationStore()
    app.dependency_overrides[get_conversation_store] = lambda: store
    app.dependency_overrides[get_video_extractor] = lambda: FakeVideoExtractor()

    with TestClient(app) as client:
        created = client.post(
            "/api/conversations",
            json={"url": "https://www.douyin.com/video/7670495404269604134"},
        )
        streamed = client.post(f"/api/conversations/{store.conversation.id}/extract/stream")

    assert created.status_code == 201
    assert created.json() == {"id": store.conversation.id}
    assert "douyin.com" not in created.text
    assert streamed.status_code == 200
    assert '"type":"result"' in streamed.text


def test_unknown_conversation_id_returns_not_found() -> None:
    app = create_app()
    app.dependency_overrides[get_conversation_store] = lambda: FakeConversationStore()

    with TestClient(app) as client:
        response = client.post(
            "/api/conversations/0198c7a0-6f66-7c75-a318-acde48009999/extract/stream"
        )

    assert response.status_code == 404


def test_user_can_continue_the_video_conversation_and_restore_messages(tmp_path) -> None:
    app = create_app(GatewayConfig(conversation_data_dir=tmp_path))
    app.dependency_overrides[get_video_extractor] = lambda: FakeVideoExtractor()
    app.dependency_overrides[get_conversation_coach] = lambda: TranscriptConversationCoach(
        FakeChatLlm()
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/conversations",
            json={"url": "https://www.douyin.com/video/7670495404269604134"},
        ).json()
        client.post(f"/api/conversations/{created['id']}/extract/stream")
        reply = client.post(
            f"/api/conversations/{created['id']}/messages",
            json={"content": "这个短语是什么意思？"},
        )
        restored = client.get(f"/api/conversations/{created['id']}")

    assert reply.status_code == 201
    assert reply.json()["message"]["content"] == (
        "ask after 在这里表示问候某人，或打听某人的健康和近况。"
    )
    assert restored.json()["video"]["transcript"] == (
        "视频解释了 ask after 表示问候或打听某人的近况。"
    )
    assert [message["role"] for message in restored.json()["messages"]] == [
        "user",
        "assistant",
    ]


def test_playback_proxies_video_bytes_with_range_headers() -> None:
    app = create_app()
    app.dependency_overrides[get_video_extractor] = lambda: FakeVideoExtractor()

    with TestClient(app) as client:
        response = client.get(
            "/api/videos/7420000000000000000/playback",
            headers={"range": "bytes=0-3"},
        )

    assert response.status_code == 206
    assert response.content == b"video"
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["content-range"] == "bytes 0-4/5"
    assert response.headers["accept-ranges"] == "bytes"
