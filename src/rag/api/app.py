from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from itertools import chain
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import requests

from ..llama_cpp import (
    build_endpoint_urls,
    filter_chat_models,
    is_embedding_model_name,
    list_remote_models,
    resolve_model_alias,
)
from ..logging import setup_logging
from ..rag import RagPipeline
from ..runtime import build_pipeline
from ..settings import Settings, load_settings

setup_logging()
settings = load_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM-RAG", version="0.1.0")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):  # noqa: ANN001
    logger.exception("Unhandled API error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.middleware("http")
async def log_timing(request, call_next):
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "HTTP %s %s -> %s in %.1f ms",
            request.method,
            request.url.path,
            getattr(getattr(response, "status_code", None), "__int__", lambda: None)(),
            elapsed_ms,
        )


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
    model = (cfg.llama_cpp.llm_model or "").strip()
    if model:
        return model
    # If no default configured, signal clearly.
    raise HTTPException(
        status_code=400,
        detail=(
            "No default model configured. "
            "Set llama_cpp.llm_model or pass 'model' in the request."
        ),
    )


def _llm_base_url(current: Optional[Settings] = None) -> str:
    cfg = current or settings
    return cfg.llama_cpp.base_url


def _build_settings_for_model(model_name: str) -> Settings:
    requested = (model_name or "").strip()
    cfg = settings.model_copy(deep=True)
    if requested:
        cfg.llama_cpp.llm_model = requested
    else:
        cfg.llama_cpp.llm_model = _configured_model_name(cfg)
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
    except Exception as exc:  # noqa: BLE001
        _raise_pipeline_http_error(exc)


def _raise_pipeline_http_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, requests.exceptions.ReadTimeout):
        raise HTTPException(
            status_code=504,
            detail="LLM request timed out. Try a smaller model or retry.",
        ) from exc
    if isinstance(exc, requests.exceptions.ConnectionError):
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach llama.cpp server at {_llm_base_url()}.",
        ) from exc
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else "unknown"
        if exc.response is not None and exc.response.status_code == 400:
            detail = exc.response.text.strip()
            if detail:
                raise HTTPException(
                    status_code=400,
                    detail=f"Upstream llama.cpp rejected the request: {detail}",
                ) from exc
        raise HTTPException(
            status_code=502,
            detail=f"Upstream LLM HTTP error ({status}).",
        ) from exc
    logger.exception("Unhandled pipeline error")
    raise HTTPException(status_code=500, detail=f"RAG internal error: {exc}") from exc


def _available_models() -> List[str]:
    endpoints = build_endpoint_urls(
        _llm_base_url(),
        settings.llama_cpp.resolved_rpc_targets(),
    )
    remote_models = list_remote_models(endpoints, settings.llama_cpp.timeout_s, logger)
    if remote_models:
        return filter_chat_models(remote_models)

    # Fallback when upstream /v1/models is unavailable.
    candidates: List[str] = []
    try:
        configured = _configured_model_name()
        basename = Path(configured).name
        candidates.extend([basename, configured])
    except HTTPException:
        pass

    deduped: List[str] = []
    for model in candidates:
        normalized = (model or "").strip()
        if normalized and normalized not in deduped and _is_chat_model_name(normalized):
            deduped.append(normalized)
    return deduped


def _is_chat_model_name(name: str) -> bool:
    return not is_embedding_model_name(name)


@app.get("/health")
def health() -> dict:
    primary_provider = settings.primary_provider()
    try:
        model_name = _configured_model_name()
    except HTTPException:
        model_name = ""
    return {
        "status": "ok",
        "provider": primary_provider,
        "model": model_name,
        "available_models": _available_models(),
    }


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    logger.info("RAG query endpoint called")
    configured_model = (settings.llama_cpp.llm_model or "").strip()
    if not configured_model:
        raise HTTPException(
            status_code=400,
            detail=(
                "No default model configured. "
                "Set llama_cpp.llm_model (or LLAMA_CPP_LLM_MODEL) "
                "or use /v1/chat/completions with an explicit model."
            ),
        )
    if is_embedding_model_name(configured_model):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Configured model '{configured_model}' looks like an embedding model. "
                "Set llama_cpp.llm_model to a chat/instruct model."
            ),
        )
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
    requested_model = resolve_model_alias(requested_model, available_models)
    if requested_model and is_embedding_model_name(requested_model):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Model '{requested_model}' looks like an embedding model. "
                "Choose a chat/instruct model."
            ),
        )
    if requested_model and available_models and requested_model not in available_models:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported model '{requested_model}'. "
                f"Available models: {', '.join(available_models)}"
            ),
        )
    logger.info("OpenAI-compatible endpoint called (stream=%s)", req.stream)
    question = _extract_user_prompt(req.messages)

    if req.stream:
        chat_id = f"chatcmpl-{uuid4().hex}"
        try:
            pipeline = get_pipeline_for_model(requested_model)
            raw_iter = iter(pipeline.answer_stream(question))
            first_chunk = next(raw_iter, None)
            model_name = _configured_model_name(pipeline.settings)
        except Exception as exc:  # noqa: BLE001
            _raise_pipeline_http_error(exc)
        stream_iter = chain(([first_chunk] if first_chunk else []), raw_iter)

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

            try:
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
            except Exception as exc:  # noqa: BLE001
                # Response has already started; log and close stream cleanly.
                logger.warning("Streaming interrupted for model %s: %s", model_name, exc)
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

    try:
        pipeline = get_pipeline_for_model(requested_model)
    except Exception as exc:  # noqa: BLE001
        _raise_pipeline_http_error(exc)
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
