from __future__ import annotations

import pytest

from app.videos.analysis import TranscriptLlmVideoAnalyzer
from app.videos.contracts import ProcessingTraceStep


class FakeTranscriber:
    async def transcribe(self, *, video_id: str, video_content: bytes) -> str:
        assert video_id == "7420000000000000000"
        assert video_content == b"video-content"
        return "北魏建立后经历十一位皇帝，孝文帝迁都洛阳并推动汉化改革。"


class FakeOneShotLlm:
    def __init__(self) -> None:
        self.system_instruction = ""
        self.user_content = ""

    async def invoke(self, *, system_instruction: str, user_content: str) -> str:
        self.system_instruction = system_instruction
        self.user_content = user_content
        return """{
          "summary": "视频梳理北魏十一位皇帝，并以孝文帝改革为关键转折。",
          "key_points": [
            "北魏皇权传承伴随宗室和权臣斗争。",
            "迁都洛阳是改革的重要节点。",
            "汉化政策改变了政权结构与文化方向。"
          ],
          "questions": ["改革为什么会引发旧贵族反弹？"]
        }"""


@pytest.mark.asyncio
async def test_transcript_llm_analyzer_summarizes_the_transcribed_video_content() -> None:
    llm = FakeOneShotLlm()
    reported_steps: list[ProcessingTraceStep] = []
    analyzer = TranscriptLlmVideoAnalyzer(
        transcriber=FakeTranscriber(),
        llm=llm,
    )

    result = await analyzer.analyze(
        video_id="7420000000000000000",
        title="北魏11位皇帝的传奇故事",
        video_content=b"video-content",
        on_progress=reported_steps.append,
    )

    assert result.transcript.startswith("北魏建立后经历十一位皇帝")
    assert result.interpretation.summary == "视频梳理北魏十一位皇帝，并以孝文帝改革为关键转折。"
    assert result.interpretation.key_points[2] == "汉化政策改变了政权结构与文化方向。"
    assert "只依据转写文本" in llm.system_instruction
    assert "北魏11位皇帝的传奇故事" not in llm.user_content
    assert result.transcript in llm.user_content
    transcription_events = [step for step in reported_steps if step.key == "audio_transcription"]
    assert [step.status for step in transcription_events] == ["running", "complete"]
    assert transcription_events[-1].data["character_count"] == len(result.transcript)
    assert transcription_events[-1].data["excerpt"] == result.transcript
    llm_events = [step for step in reported_steps if step.key == "llm_interpretation"]
    assert [step.status for step in llm_events] == ["running", "complete"]
    assert llm_events[-1].data == {
        "summary_excerpt": "视频梳理北魏十一位皇帝，并以孝文帝改革为关键转折。",
        "key_point_count": 3,
        "question_count": 1,
    }
