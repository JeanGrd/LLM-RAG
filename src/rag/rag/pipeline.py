from __future__ import annotations

import logging
import re
from typing import Iterable, List, Optional

from ..embeddings import Embeddings
from ..llm import LLM
from ..models import RagResponse, RetrievalResult
from ..settings import Settings
from ..vectorstore import VectorStore
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)
MAX_CONTEXT_SNIPPET_CHARS = 1400
RETRIEVAL_OVERSAMPLING_FACTOR = 5


class RagPipeline:
    def __init__(
        self,
        embeddings: Embeddings,
        vectorstore: VectorStore,
        llm_cloud: LLM,
        llm_ollama: LLM,
        settings: Settings,
    ) -> None:
        self.embeddings = embeddings
        self.vectorstore = vectorstore
        self.llm_cloud = llm_cloud
        self.llm_ollama = llm_ollama
        self.settings = settings

    def retrieve(self, question: str) -> List[RetrievalResult]:
        query_embedding = self.embeddings.embed_texts([question])[0]
        candidate_k = max(
            self.settings.rag.top_k,
            self.settings.rag.top_k * RETRIEVAL_OVERSAMPLING_FACTOR,
        )
        return self.vectorstore.query(query_embedding, candidate_k)

    def _build_context(self, results: List[RetrievalResult]) -> str:
        parts = []
        for r in results:
            source = r.metadata.get("source", r.doc_id)
            text = (r.text or "").strip()
            if len(text) > MAX_CONTEXT_SNIPPET_CHARS:
                text = f"{text[:MAX_CONTEXT_SNIPPET_CHARS]}..."
            parts.append(f"[{source}] {text}")
        return "\n\n".join(parts)

    def _query_terms(self, question: str) -> set[str]:
        terms = re.findall(r"[A-Za-z0-9]+", question.lower())
        return {term for term in terms if len(term) >= 3}

    def _keyword_overlap(self, result: RetrievalResult, terms: set[str]) -> int:
        if not terms:
            return 0
        source = str(result.metadata.get("source", result.doc_id)).lower()
        text = (result.text or "").lower()
        haystack = f"{source}\n{text}"
        return sum(1 for term in terms if term in haystack)

    def _rerank_results(self, results: List[RetrievalResult], question: str) -> List[RetrievalResult]:
        terms = self._query_terms(question)
        if not terms:
            return results
        return sorted(
            results,
            key=lambda r: (self._keyword_overlap(r, terms), r.score),
            reverse=True,
        )

    def _get_llm(self, provider: str) -> LLM:
        if provider == "cloud":
            return self.llm_cloud
        return self.llm_ollama

    def _get_model_name(self, provider: str) -> str:
        llm = self._get_llm(provider)
        return getattr(llm, "model", provider)

    def _fallback_provider(self, provider: str) -> Optional[str]:
        # Keep backward compatibility: fallback path is cloud -> ollama only.
        if provider == "cloud":
            return "ollama"
        return None

    def _generate(self, provider: str, prompt: str) -> str:
        llm = self._get_llm(provider)
        return llm.generate(prompt, system_prompt=SYSTEM_PROMPT)

    def _generate_stream(self, provider: str, prompt: str) -> Iterable[str]:
        llm = self._get_llm(provider)
        return llm.stream(prompt, system_prompt=SYSTEM_PROMPT)

    def answer(self, question: str) -> RagResponse:
        results = self.retrieve(question)
        if self.settings.rag.min_score > 0:
            results = [r for r in results if r.score >= self.settings.rag.min_score]
        results = self._rerank_results(results, question)
        results = results[: self.settings.rag.top_k]
        context = self._build_context(results)
        prompt = USER_PROMPT_TEMPLATE.format(question=question, context=context)

        primary_provider = self.settings.primary_provider()
        used_fallback = False
        model_name = self._get_model_name(primary_provider)
        try:
            answer = self._generate(primary_provider, prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s LLM failed: %s", primary_provider, exc)
            fallback_provider = self._fallback_provider(primary_provider)
            if not self.settings.rag.fallback_to_ollama or fallback_provider is None:
                raise
            answer = self._generate(fallback_provider, prompt)
            used_fallback = True
            model_name = self._get_model_name(fallback_provider)

        return RagResponse(
            answer=answer,
            sources=results,
            model=model_name,
            used_fallback=used_fallback,
        )

    def answer_stream(self, question: str) -> Iterable[str]:
        """
        Stream only the answer text (no metadata). Keeps same retrieval/prompting as answer().
        """
        results = self.retrieve(question)
        if self.settings.rag.min_score > 0:
            results = [r for r in results if r.score >= self.settings.rag.min_score]
        results = self._rerank_results(results, question)
        results = results[: self.settings.rag.top_k]
        context = self._build_context(results)
        prompt = USER_PROMPT_TEMPLATE.format(question=question, context=context)

        primary_provider = self.settings.primary_provider()
        model_name = self._get_model_name(primary_provider)
        try:
            return self._generate_stream(primary_provider, prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s LLM failed in stream mode: %s", primary_provider, exc)
            fallback_provider = self._fallback_provider(primary_provider)
            if not self.settings.rag.fallback_to_ollama or fallback_provider is None:
                raise
            model_name = self._get_model_name(fallback_provider)
            return self._generate_stream(fallback_provider, prompt)
