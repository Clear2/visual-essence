from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONVERSATION_DATA_DIR = Path(__file__).resolve().parents[3] / "data/conversations"


def _resolve_env_reference(value: object) -> str:
    normalized = str(value or "").strip()
    if normalized.startswith("$"):
        return os.getenv(normalized[1:], "").strip()
    return normalized


def _runtime_config() -> dict[str, Any]:
    explicit = os.getenv("VISUAL_ESSENCE_CONFIG_PATH", "").strip()
    candidates = [Path(explicit)] if explicit else [Path("config.yaml"), Path("../config.yaml")]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as error:
        raise RuntimeError(f"无法读取 Visual Essence 配置文件：{path}") from error
    if not isinstance(loaded, dict):
        raise RuntimeError("Visual Essence 配置文件的顶层必须是对象。")
    return loaded


def _enabled(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class ModelDefinition:
    name: str
    use: str
    model: str
    api_key: str = field(default="", repr=False)
    settings: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ModelDefinition:
        excluded = {
            "name",
            "display_name",
            "description",
            "use",
            "model",
            "api_key",
            "supports_thinking",
            "supports_reasoning_effort",
            "supports_vision",
            "when_thinking_enabled",
            "when_thinking_disabled",
            "thinking",
            "pricing",
        }
        settings = {key: item for key, item in value.items() if key not in excluded}
        if "api_base" in settings and "base_url" not in settings:
            settings["base_url"] = settings.pop("api_base")
        return cls(
            name=str(value.get("name") or "").strip(),
            use=str(value.get("use") or "langchain_openai:ChatOpenAI").strip(),
            model=str(value.get("model") or "").strip(),
            api_key=_resolve_env_reference(value.get("api_key")),
            settings=settings,
        )


@dataclass(frozen=True, slots=True)
class VideoAnalysisConfig:
    enabled: bool = False
    model_name: str | None = None
    transcription_api_url: str = "https://api.openai.com/v1/audio/transcriptions"
    transcription_api_key: str = field(default="", repr=False)
    transcription_model: str = "gpt-4o-mini-transcribe"
    transcription_provider: str = "openai"
    whisper_cli_path: str = "whisper-cli"
    whisper_model_path: str = ""
    whisper_language: str = "zh"
    request_timeout_seconds: float = 180.0
    max_video_bytes: int = 200 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    """Process-level gateway configuration loaded from environment variables."""

    app_name: str = "Visual Essence API"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    upstream_timeout_seconds: float = 12.0
    upstream_max_redirects: int = 5
    upstream_max_response_bytes: int = 5 * 1024 * 1024
    conversation_data_dir: Path = _DEFAULT_CONVERSATION_DATA_DIR
    models: tuple[ModelDefinition, ...] = ()
    video_analysis: VideoAnalysisConfig = field(default_factory=VideoAnalysisConfig)

    def get_model(self, name: str | None = None) -> ModelDefinition | None:
        if name:
            return next((model for model in self.models if model.name == name), None)
        return self.models[0] if self.models else None

    @classmethod
    def from_env(cls) -> GatewayConfig:
        runtime = _runtime_config()
        raw_models = runtime.get("models") if isinstance(runtime.get("models"), list) else []
        models = tuple(
            model
            for item in raw_models
            if isinstance(item, dict)
            if (model := ModelDefinition.from_mapping(item)).name and model.model
        )
        env_model = os.getenv("VISUAL_ESSENCE_LLM_MODEL", "").strip()
        env_api_key = os.getenv("VISUAL_ESSENCE_LLM_API_KEY", "").strip()
        if not models and env_model:
            settings: dict[str, Any] = {}
            if base_url := os.getenv("VISUAL_ESSENCE_LLM_BASE_URL", "").strip():
                settings["base_url"] = base_url
            models = (
                ModelDefinition(
                    name="video-analysis",
                    use="langchain_openai:ChatOpenAI",
                    model=env_model,
                    api_key=env_api_key,
                    settings=settings,
                ),
            )

        raw_analysis = (
            runtime.get("video_analysis") if isinstance(runtime.get("video_analysis"), dict) else {}
        )
        enabled_value: object = raw_analysis.get("enabled", False)
        if "VISUAL_ESSENCE_VIDEO_ANALYSIS_ENABLED" in os.environ:
            enabled_value = os.environ["VISUAL_ESSENCE_VIDEO_ANALYSIS_ENABLED"]
        transcription_key = os.getenv("VISUAL_ESSENCE_TRANSCRIPTION_API_KEY", "").strip()
        if not transcription_key:
            transcription_key = _resolve_env_reference(raw_analysis.get("transcription_api_key"))
        analysis_config = VideoAnalysisConfig(
            enabled=_enabled(enabled_value),
            model_name=(
                os.getenv("VISUAL_ESSENCE_LLM_MODEL_NAME", "").strip()
                or str(raw_analysis.get("model_name") or "").strip()
                or None
            ),
            transcription_api_url=(
                os.getenv("VISUAL_ESSENCE_TRANSCRIPTION_API_URL", "").strip()
                or str(raw_analysis.get("transcription_api_url") or "").strip()
                or "https://api.openai.com/v1/audio/transcriptions"
            ),
            transcription_api_key=transcription_key,
            transcription_model=(
                os.getenv("VISUAL_ESSENCE_TRANSCRIPTION_MODEL", "").strip()
                or str(raw_analysis.get("transcription_model") or "").strip()
                or "gpt-4o-mini-transcribe"
            ),
            transcription_provider=(
                os.getenv("VISUAL_ESSENCE_TRANSCRIPTION_PROVIDER", "").strip()
                or str(raw_analysis.get("transcription_provider") or "").strip()
                or "openai"
            ),
            whisper_cli_path=(
                os.getenv("VISUAL_ESSENCE_WHISPER_CLI_PATH", "").strip()
                or str(raw_analysis.get("whisper_cli_path") or "").strip()
                or "whisper-cli"
            ),
            whisper_model_path=(
                os.getenv("VISUAL_ESSENCE_WHISPER_MODEL_PATH", "").strip()
                or _resolve_env_reference(raw_analysis.get("whisper_model_path"))
            ),
            whisper_language=(
                os.getenv("VISUAL_ESSENCE_WHISPER_LANGUAGE", "").strip()
                or str(raw_analysis.get("whisper_language") or "").strip()
                or "zh"
            ),
            request_timeout_seconds=float(raw_analysis.get("request_timeout_seconds") or 180),
            max_video_bytes=int(raw_analysis.get("max_video_bytes") or 200 * 1024 * 1024),
        )
        origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "VISUAL_ESSENCE_CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        )
        return cls(
            host=os.getenv("VISUAL_ESSENCE_HOST", "0.0.0.0"),
            port=int(os.getenv("VISUAL_ESSENCE_PORT", "8000")),
            cors_origins=origins,
            upstream_timeout_seconds=float(
                os.getenv("VISUAL_ESSENCE_UPSTREAM_TIMEOUT_SECONDS", "12")
            ),
            conversation_data_dir=Path(
                os.getenv(
                    "VISUAL_ESSENCE_CONVERSATION_DATA_DIR",
                    str(_DEFAULT_CONVERSATION_DATA_DIR),
                )
            ),
            models=models,
            video_analysis=analysis_config,
        )


@lru_cache(maxsize=1)
def get_gateway_config() -> GatewayConfig:
    return GatewayConfig.from_env()
