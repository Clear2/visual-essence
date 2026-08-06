from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.conversations.coach import TranscriptConversationCoach
from app.conversations.store import FileConversationStore
from app.gateway.config import GatewayConfig, get_gateway_config
from app.gateway.routers import conversations, health, videos
from app.videos.analysis import (
    LocalWhisperCliTranscriber,
    OpenAiAudioTranscriber,
    TranscriptLlmVideoAnalyzer,
)
from app.videos.extractor import VideoExtractionModule
from app.videos.llm import LangChainOneShotLlm


def create_app(config: GatewayConfig | None = None) -> FastAPI:
    gateway_config = config or get_gateway_config()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        timeout = httpx.Timeout(gateway_config.upstream_timeout_seconds)
        analysis_timeout = httpx.Timeout(gateway_config.video_analysis.request_timeout_seconds)
        async with (
            httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                limits=httpx.Limits(max_connections=40, max_keepalive_connections=10),
            ) as client,
            httpx.AsyncClient(timeout=analysis_timeout) as analysis_client,
        ):
            video_analyzer = None
            conversation_coach = None
            if gateway_config.video_analysis.enabled:
                model = gateway_config.get_model(gateway_config.video_analysis.model_name)
                if model is None:
                    raise RuntimeError("视频分析已启用，但没有找到可用的 LLM 模型配置。")
                transcription_key = (
                    gateway_config.video_analysis.transcription_api_key or model.api_key
                )
                if gateway_config.video_analysis.transcription_provider == "local_whisper":
                    transcriber = LocalWhisperCliTranscriber(
                        cli_path=gateway_config.video_analysis.whisper_cli_path,
                        model_path=gateway_config.video_analysis.whisper_model_path,
                        language=gateway_config.video_analysis.whisper_language,
                        max_video_bytes=gateway_config.video_analysis.max_video_bytes,
                        timeout_seconds=gateway_config.video_analysis.request_timeout_seconds,
                    )
                else:
                    transcriber = OpenAiAudioTranscriber(
                        client=analysis_client,
                        api_url=gateway_config.video_analysis.transcription_api_url,
                        api_key=transcription_key,
                        model=gateway_config.video_analysis.transcription_model,
                        max_video_bytes=gateway_config.video_analysis.max_video_bytes,
                    )
                language_model = LangChainOneShotLlm(model)
                video_analyzer = TranscriptLlmVideoAnalyzer(
                    transcriber=transcriber,
                    llm=language_model,
                )
                conversation_coach = TranscriptConversationCoach(language_model)
            application.state.video_extractor = VideoExtractionModule(
                client,
                max_redirects=gateway_config.upstream_max_redirects,
                max_response_bytes=gateway_config.upstream_max_response_bytes,
                video_analyzer=video_analyzer,
            )
            application.state.conversation_store = FileConversationStore(
                gateway_config.conversation_data_dir
            )
            application.state.conversation_coach = conversation_coach
            yield

    application = FastAPI(
        title=gateway_config.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(gateway_config.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.include_router(health.router)
    application.include_router(conversations.router)
    application.include_router(videos.router)
    return application


app = create_app()
