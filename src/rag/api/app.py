from __future__ import annotations

from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from ..embeddings import OllamaEmbeddings
from ..llm import CloudLLM, OllamaLLM
from ..logging import setup_logging
from ..rag import RagPipeline
from ..settings import load_settings
from ..vectorstore import ChromaVectorStore

setup_logging()
settings = load_settings()

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


pipeline = RagPipeline(
    embeddings=OllamaEmbeddings(
        base_url=settings.ollama.base_url,
        model=settings.ollama.embed_model,
        timeout_s=settings.ollama.timeout_s,
    ),
    vectorstore=ChromaVectorStore(index_dir=settings.paths.index_dir),
    llm_cloud=CloudLLM(
        api_url=settings.cloud.api_url,
        api_key=settings.cloud.api_key,
        model=settings.cloud.model,
        timeout_s=settings.cloud.timeout_s,
    ),
    llm_fallback=OllamaLLM(
        base_url=settings.ollama.base_url,
        model=settings.ollama.llm_model,
        timeout_s=settings.ollama.timeout_s,
    ),
    settings=settings,
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    resp = pipeline.answer(req.question)
    sources = [
        SourceItem(doc_id=s.doc_id, score=s.score, metadata=s.metadata) for s in resp.sources
    ]
    return QueryResponse(
        answer=resp.answer,
        sources=sources,
        model=resp.model,
        used_fallback=resp.used_fallback,
    )
