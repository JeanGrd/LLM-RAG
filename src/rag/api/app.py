from __future__ import annotations

import logging
import time
from uuid import uuid4

from functools import lru_cache
from typing import List, Optional

import requests
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..logging import setup_logging
from ..rag import RagPipeline
from ..runtime import build_pipeline
from ..settings import Settings, load_settings

setup_logging()
settings = load_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM-RAG", version="0.1.0")


class QueryRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    doc_id: str
    score: float
    metadata: dict


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    model: str
    used_fallback: bool


class OpenAIMessage(BaseModel):
    role: str
    content: str


class OpenAIChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[OpenAIMessage]
    stream: bool = False


class OpenAIChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIChoiceMessage
    finish_reason: str = "stop"


class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]


class OpenAIModel(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "llm-rag"


class OpenAIModelsResponse(BaseModel):
    object: str = "list"
    data: List[OpenAIModel]


@lru_cache(maxsize=1)
def get_pipeline() -> RagPipeline:
    return build_pipeline(settings)


def _configured_model_name(current: Optional[Settings] = None) -> str:
    cfg = current or settings
    provider = cfg.primary_provider()
    return cfg.model.name or (cfg.cloud.model if provider == "cloud" else cfg.ollama.llm_model)


def _build_settings_for_model(model_name: str) -> Settings:
    requested = model_name.strip()
    if not requested:
        return settings

    cfg = settings.model_copy(deep=True)
    if requested == cfg.cloud.model:
        cfg.model.provider = "cloud"
    else:
        cfg.model.provider = "ollama"
    cfg.model.name = requested
    return cfg


@lru_cache(maxsize=8)
def get_pipeline_for_model(model_name: str) -> RagPipeline:
    return build_pipeline(_build_settings_for_model(model_name))


def _extract_user_prompt(messages: List[OpenAIMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            content = message.content.strip()
            if content:
                return content
    raise HTTPException(status_code=400, detail="At least one non-empty user message is required")


def _run_pipeline_answer(pipeline: RagPipeline, question: str):
    try:
        return pipeline.answer(question)
    except requests.exceptions.ReadTimeout as exc:
        raise HTTPException(
            status_code=504,
            detail="LLM request timed out. Try a smaller model or retry.",
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Ollama at {settings.ollama.base_url}.",
        ) from exc
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise HTTPException(
            status_code=502,
            detail=f"Upstream LLM HTTP error ({status}).",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled pipeline error")
        raise HTTPException(status_code=500, detail=f"RAG internal error: {exc}") from exc


def _available_models() -> List[str]:
    ollama_models = [m for m in _list_ollama_models() if _is_chat_model_name(m)]

    # Always expose the configured runtime model even if model discovery fails.
    candidates: List[str] = [_configured_model_name()]
    if settings.cloud.model and settings.cloud.model != "best-model":
        candidates.append(settings.cloud.model.strip())

    # Expose installed Ollama chat models to enable multi-model selection from Open WebUI.
    candidates.extend(ollama_models)

    deduped: List[str] = []
    seen = set()
    for model in candidates:
        normalized = model.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _list_ollama_models() -> List[str]:
    try:
        resp = requests.get(
            f"{settings.ollama.base_url.rstrip('/')}/api/tags",
            timeout=min(settings.ollama.timeout_s, 10),
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to list Ollama models from %s: %s", settings.ollama.base_url, exc)
        return []

    models = payload.get("models", [])
    names: List[str] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if isinstance(name, str):
            names.append(name)
    return names


def _is_chat_model_name(name: str) -> bool:
    lowered = name.lower()
    return "embed" not in lowered and "embedding" not in lowered


@app.get("/health")
def health() -> dict:
    primary_provider = settings.primary_provider()
    return {
        "status": "ok",
        "provider": primary_provider,
        "model": _configured_model_name(),
        "available_models": _available_models(),
    }


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    logger.info("RAG query endpoint called")
    resp = _run_pipeline_answer(get_pipeline(), req.question)
    sources = [
        SourceItem(doc_id=s.doc_id, score=s.score, metadata=s.metadata) for s in resp.sources
    ]
    return QueryResponse(
        answer=resp.answer,
        sources=sources,
        model=resp.model,
        used_fallback=resp.used_fallback,
    )


@app.get("/v1/models", response_model=OpenAIModelsResponse)
def list_models() -> OpenAIModelsResponse:
    return OpenAIModelsResponse(data=[OpenAIModel(id=model) for model in _available_models()])


@app.post("/v1/chat/completions", response_model=OpenAIChatResponse)
def openai_chat_completions(req: OpenAIChatRequest) -> OpenAIChatResponse:
    requested_model = (req.model or "").strip()
    available_models = _available_models()
    if requested_model and requested_model not in available_models:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{requested_model}'. Available models: {', '.join(available_models)}",
        )
    logger.info("OpenAI-compatible endpoint called (stream=%s)", req.stream)
    question = _extract_user_prompt(req.messages)

    if req.stream:
        chat_id = f"chatcmpl-{uuid4().hex}"
        pipeline = get_pipeline_for_model(requested_model)
        stream_iter = pipeline.answer_stream(question)
        model_name = _configured_model_name(pipeline.settings)

        def event_stream():
            # First chunk: send assistant role so some clients start rendering immediately.
            role_payload = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(role_payload)}\n\n"

            for chunk in stream_iter:
                payload = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(payload)}\n\n"
            yield (
                "data: "
                + json.dumps(
                    {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model_name,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop",
                            }
                        ],
                    }
                )
                + "\n\n"
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # disable nginx/proxy buffering
            },
        )

    pipeline = get_pipeline_for_model(requested_model)
    result = _run_pipeline_answer(pipeline, question)
    return OpenAIChatResponse(
        id=f"chatcmpl-{uuid4().hex}",
        created=int(time.time()),
        model=result.model,
        choices=[
            OpenAIChoice(
                message=OpenAIChoiceMessage(content=result.answer),
            )
        ],
    )
