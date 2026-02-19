from __future__ import annotations

from typing import Optional

from .embeddings import LlamaCppEmbeddings
from .llama_cpp import (
    build_endpoint_urls,
    filter_chat_models,
    filter_embedding_models,
    is_embedding_model_name,
    list_remote_models,
    resolve_model_alias,
)
from .llm import LlamaCppLLM
from .rag import RagPipeline
from .settings import Settings, load_settings
from .vectorstore import ChromaVectorStore


def _resolve_model(settings: Settings) -> str:
    model = (settings.llama_cpp.llm_model or "").strip()
    if not model:
        raise ValueError(
            "No default llama.cpp model configured. "
            "Set llama_cpp.llm_model or pass model per request."
        )
    return model


def _resolve_chat_model(configured_model: str, remote_models: list[str]) -> str:
    resolved = resolve_model_alias(configured_model, remote_models)
    chat_models = filter_chat_models(remote_models)

    # Keep the service usable when config points to a stale/absent model id.
    if remote_models and resolved not in remote_models and chat_models:
        return chat_models[0]

    if not is_embedding_model_name(resolved):
        return resolved

    if chat_models:
        return chat_models[0]

    raise ValueError(
        f"Configured model '{configured_model}' looks like an embedding model. "
        "Set llama_cpp.llm_model to a chat/instruct model."
    )


def build_pipeline(settings: Optional[Settings] = None) -> RagPipeline:
    runtime_settings = settings or load_settings()
    rpc_targets = runtime_settings.llama_cpp.resolved_rpc_targets()
    base_url = runtime_settings.llama_cpp.base_url
    endpoints = build_endpoint_urls(base_url, rpc_targets)
    remote_models = list_remote_models(endpoints, runtime_settings.llama_cpp.timeout_s)

    llm_model = _resolve_chat_model(_resolve_model(runtime_settings), remote_models)
    embed_model_config = (runtime_settings.llama_cpp.embed_model or "").strip()
    if embed_model_config:
        embed_model = resolve_model_alias(embed_model_config, remote_models)
    else:
        embedding_models = filter_embedding_models(remote_models)
        embed_model = embedding_models[0] if embedding_models else llm_model

    return RagPipeline(
        embeddings=LlamaCppEmbeddings(
            base_url=base_url,
            model=embed_model,
            timeout_s=runtime_settings.llama_cpp.timeout_s,
            rpc_targets=rpc_targets,
        ),
        vectorstore=ChromaVectorStore(index_dir=runtime_settings.paths.index_dir),
        llm=LlamaCppLLM(
            base_url=base_url,
            model=llm_model,
            timeout_s=runtime_settings.llama_cpp.timeout_s,
            rpc_targets=rpc_targets,
        ),
        settings=runtime_settings,
    )
