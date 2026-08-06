from __future__ import annotations

import importlib
import os
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.gateway.config import ModelDefinition
from app.videos.errors import VideoAnalysisError


def _resolve_setting(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        return os.getenv(value[1:], "")
    if isinstance(value, dict):
        return {key: _resolve_setting(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_setting(item) for item in value]
    return value


def _model_class(path: str) -> type[BaseChatModel]:
    separator = ":" if ":" in path else "."
    module_name, class_name = path.rsplit(separator, 1)
    try:
        candidate = getattr(importlib.import_module(module_name), class_name)
    except (ImportError, AttributeError) as error:
        raise VideoAnalysisError("LLM 模型类配置无效。") from error
    if not isinstance(candidate, type) or not issubclass(candidate, BaseChatModel):
        raise VideoAnalysisError("LLM 模型类配置无效。")
    return candidate


def _response_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(text := getattr(item, "text", None), str):
                parts.append(text)
        return "".join(parts)
    return str(content or "")


class LangChainOneShotLlm:
    """One-shot System + Human model invocation through LangChain."""

    def __init__(self, model_definition: ModelDefinition) -> None:
        if not model_definition.api_key:
            raise VideoAnalysisError("LLM API Key 尚未配置。")
        settings = _resolve_setting(model_definition.settings)
        settings["model"] = model_definition.model
        settings["api_key"] = model_definition.api_key
        self._model = _model_class(model_definition.use)(**settings)

    async def invoke(self, *, system_instruction: str, user_content: str) -> str:
        try:
            response = await self._model.ainvoke(
                [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=user_content),
                ],
                config={"run_name": "visual_essence_video_interpretation"},
            )
        except Exception as error:
            raise VideoAnalysisError("语言模型暂时无法生成视频解读。") from error
        content = _response_text(response.content).strip()
        if not content:
            raise VideoAnalysisError("语言模型返回了空解读。")
        return content
