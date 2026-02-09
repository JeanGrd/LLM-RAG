from __future__ import annotations

import logging
from typing import List

from ..embeddings import Embeddings
from ..llm import LLM
from ..models import RagResponse, RetrievalResult
from ..settings import Settings
from ..vectorstore import VectorStore
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class RagPipeline:
    def __init__(
        self,
        embeddings: Embeddings,
        vectorstore: VectorStore,
        llm_cloud: LLM,
        llm_fallback: LLM,
        settings: Settings,
    ) -> None:
        self.embeddings = embeddings
        self.vectorstore = vectorstore
        self.llm_cloud = llm_cloud
        self.llm_fallback = llm_fallback
        self.settings = settings

    def retrieve(self, question: str) -> List[RetrievalResult]:
        query_embedding = self.embeddings.embed_texts([question])[0]
        return self.vectorstore.query(query_embedding, self.settings.rag.top_k)

    def _build_context(self, results: List[RetrievalResult]) -> str:
        parts = []
        for r in results:
            source = r.metadata.get("source", r.doc_id)
            parts.append(f"[{source}] {r.text}")
        return "\n\n".join(parts)

    def _generate_with_llm(self, prompt: str) -> str:
        return self.llm_cloud.generate(prompt, system_prompt=SYSTEM_PROMPT)

    def _generate_with_fallback(self, prompt: str) -> str:
        return self.llm_fallback.generate(prompt, system_prompt=SYSTEM_PROMPT)

    def answer(self, question: str) -> RagResponse:
        results = self.retrieve(question)
        if self.settings.rag.min_score > 0:
            results = [r for r in results if r.score >= self.settings.rag.min_score]
        context = self._build_context(results)
        prompt = USER_PROMPT_TEMPLATE.format(question=question, context=context)

        used_fallback = False
        model_name = "cloud"
        try:
            if self.settings.rag.use_cloud_first:
                answer = self._generate_with_llm(prompt)
            else:
                answer = self._generate_with_fallback(prompt)
                used_fallback = True
                model_name = "ollama"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloud LLM failed: %s", exc)
            if not self.settings.rag.fallback_to_ollama:
                raise
            answer = self._generate_with_fallback(prompt)
            used_fallback = True
            model_name = "ollama"

        return RagResponse(
            answer=answer,
            sources=results,
            model=model_name,
            used_fallback=used_fallback,
        )
