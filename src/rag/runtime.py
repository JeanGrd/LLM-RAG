from __future__ import annotations

from typing import Optional

from .embeddings import OllamaEmbeddings
from .llm import OllamaLLM
from .rag import RagPipeline
from .settings import Settings, load_settings
from .vectorstore import ChromaVectorStore


def _resolve_model(settings: Settings) -> str:
    model = (settings.ollama.llm_model or "").strip()
    if not model:
        raise ValueError("No default Ollama model configured. Set ollama.llm_model or pass model per request.")
    return model


def build_pipeline(settings: Optional[Settings] = None) -> RagPipeline:
    runtime_settings = settings or load_settings()
    ollama_model = _resolve_model(runtime_settings)
    return RagPipeline(
        embeddings=OllamaEmbeddings(
            base_url=runtime_settings.ollama.base_url,
            model=runtime_settings.ollama.embed_model,
            timeout_s=runtime_settings.ollama.timeout_s,
        ),
        vectorstore=ChromaVectorStore(index_dir=runtime_settings.paths.index_dir),
        llm_ollama=OllamaLLM(
            base_url=runtime_settings.ollama.base_url,
            model=ollama_model,
            timeout_s=runtime_settings.ollama.timeout_s,
        ),
        settings=runtime_settings,
    )
