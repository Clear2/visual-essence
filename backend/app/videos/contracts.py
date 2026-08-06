from enum import StrEnum

from pydantic import BaseModel, Field


class VideoPlatform(StrEnum):
    DOUYIN = "douyin"


class ExtractionStatus(StrEnum):
    METADATA = "metadata"
    ANALYZED = "analyzed"


class ProcessingStepStatus(StrEnum):
    RUNNING = "running"
    COMPLETE = "complete"
    WARNING = "warning"


class ProcessingStepKind(StrEnum):
    OBSERVATION = "observation"
    TOOL = "tool"
    DECISION = "decision"
    RESULT = "result"
    WARNING = "warning"


class ProcessingTraceStep(BaseModel):
    key: str
    title: str
    detail: str
    kind: ProcessingStepKind = ProcessingStepKind.RESULT
    data: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    elapsed_ms: int = Field(default=0, ge=0)
    status: ProcessingStepStatus = ProcessingStepStatus.COMPLETE


class ExtractVideoRequest(BaseModel):
    url: str = Field(
        min_length=1,
        max_length=4096,
        description="A public video URL or copied share text containing one URL.",
    )


class VideoAuthor(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


class VideoCoachInterpretation(BaseModel):
    summary: str
    key_points: list[str] = Field(min_length=1)
    questions: list[str] = Field(default_factory=list)


class VideoContentResponse(BaseModel):
    platform: VideoPlatform
    status: ExtractionStatus = ExtractionStatus.METADATA
    source_url: str
    canonical_url: str
    video_id: str | None = None
    title: str
    description: str | None = None
    author: VideoAuthor = Field(default_factory=VideoAuthor)
    cover_url: str | None = None
    playback_url: str | None = None
    duration_seconds: float | None = None
    transcript: str | None = None
    coach_interpretation: VideoCoachInterpretation | None = None
    warnings: list[str] = Field(default_factory=list)
    processing_trace: list[ProcessingTraceStep] = Field(default_factory=list)
