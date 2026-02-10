import pytest

from rag.embeddings.base import Embeddings
from rag.llm.base import LLM
from rag.models import RetrievalResult
from rag.rag import RagPipeline
from rag.settings import Settings
from rag.vectorstore.base import VectorStore


class DummyEmbeddings(Embeddings):
    def embed_texts(self, texts):
        return [[0.0] * 3 for _ in texts]


class DummyVectorStore(VectorStore):
    def add(self, documents, embeddings):
        return None

    def query(self, query_embedding, top_k):
        return [
            RetrievalResult(
                doc_id="doc#1",
                text="context",
                score=0.9,
                metadata={"source": "doc"},
            )
        ]


class DummyLLM(LLM):
    def generate(self, prompt, system_prompt=None):
        return "ok"


class RecorderLLM(LLM):
    def __init__(self, model: str, should_fail: bool = False):
        self.model = model
        self.should_fail = should_fail
        self.calls = 0

    def generate(self, prompt, system_prompt=None):
        self.calls += 1
        if self.should_fail:
            raise RuntimeError(f"{self.model} failed")
        return f"ok:{self.model}"


def test_pipeline_answer():
    settings = Settings()
    pipeline = RagPipeline(
        embeddings=DummyEmbeddings(),
        vectorstore=DummyVectorStore(),
        llm_cloud=DummyLLM(),
        llm_ollama=DummyLLM(),
        settings=settings,
    )
    resp = pipeline.answer("hello")
    assert resp.answer == "ok"
    assert resp.sources


def test_pipeline_uses_configured_primary_provider():
    settings = Settings(
        model={"provider": "ollama"},
    )
    cloud = RecorderLLM("cloud-model")
    ollama = RecorderLLM("ollama-model")
    pipeline = RagPipeline(
        embeddings=DummyEmbeddings(),
        vectorstore=DummyVectorStore(),
        llm_cloud=cloud,
        llm_ollama=ollama,
        settings=settings,
    )

    resp = pipeline.answer("hello")

    assert resp.answer == "ok:ollama-model"
    assert resp.model == "ollama-model"
    assert resp.used_fallback is False
    assert ollama.calls == 1
    assert cloud.calls == 0


def test_pipeline_fallbacks_to_other_provider_on_failure():
    settings = Settings(
        model={"provider": "cloud"},
        rag={"fallback_to_ollama": True},
    )
    cloud = RecorderLLM("cloud-model", should_fail=True)
    ollama = RecorderLLM("ollama-model")
    pipeline = RagPipeline(
        embeddings=DummyEmbeddings(),
        vectorstore=DummyVectorStore(),
        llm_cloud=cloud,
        llm_ollama=ollama,
        settings=settings,
    )

    resp = pipeline.answer("hello")

    assert resp.answer == "ok:ollama-model"
    assert resp.model == "ollama-model"
    assert resp.used_fallback is True
    assert cloud.calls == 1
    assert ollama.calls == 1


def test_pipeline_raises_when_fallback_disabled():
    settings = Settings(
        model={"provider": "cloud"},
        rag={"fallback_to_ollama": False},
    )
    pipeline = RagPipeline(
        embeddings=DummyEmbeddings(),
        vectorstore=DummyVectorStore(),
        llm_cloud=RecorderLLM("cloud-model", should_fail=True),
        llm_ollama=RecorderLLM("ollama-model"),
        settings=settings,
    )

    with pytest.raises(RuntimeError):
        pipeline.answer("hello")


def test_pipeline_does_not_fallback_when_primary_is_ollama():
    settings = Settings(
        model={"provider": "ollama"},
        rag={"fallback_to_ollama": True},
    )
    pipeline = RagPipeline(
        embeddings=DummyEmbeddings(),
        vectorstore=DummyVectorStore(),
        llm_cloud=RecorderLLM("cloud-model"),
        llm_ollama=RecorderLLM("ollama-model", should_fail=True),
        settings=settings,
    )

    with pytest.raises(RuntimeError):
        pipeline.answer("hello")
