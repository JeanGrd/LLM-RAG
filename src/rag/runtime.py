from __future__ import annotations

from typing import Optional

from .embeddings import OllamaEmbeddings
from .llm import CloudLLM, OllamaLLM
from .rag import RagPipeline
from .settings import Settings, load_settings
from .vectorstore import ChromaVectorStore


def _resolve_models(settings: Settings) -> tuple[str, str]:
    cloud_model = settings.cloud.model
    ollama_model = settings.ollama.llm_model
    model_override = settings.model.name.strip()
    if model_override:
        if settings.primary_provider() == "cloud":
            cloud_model = model_override
        else:
            ollama_model = model_override
    return cloud_model, ollama_model


def build_pipeline(settings: Optional[Settings] = None) -> RagPipeline:
    runtime_settings = settings or load_settings()
    cloud_model, ollama_model = _resolve_models(runtime_settings)
    return RagPipeline(
        embeddings=OllamaEmbeddings(
            base_url=runtime_settings.ollama.base_url,
            model=runtime_settings.ollama.embed_model,
            timeout_s=runtime_settings.ollama.timeout_s,
        ),
        vectorstore=ChromaVectorStore(index_dir=runtime_settings.paths.index_dir),
        llm_cloud=CloudLLM(
            api_url=runtime_settings.cloud.api_url,
            api_key=runtime_settings.cloud.api_key,
            model=cloud_model,
            timeout_s=runtime_settings.cloud.timeout_s,
        ),
        llm_ollama=OllamaLLM(
            base_url=runtime_settings.ollama.base_url,
            model=ollama_model,
            timeout_s=runtime_settings.ollama.timeout_s,
        ),
        settings=runtime_settings,
    )
