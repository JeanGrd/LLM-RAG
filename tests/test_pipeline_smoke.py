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


def test_pipeline_answer():
    settings = Settings()
    pipeline = RagPipeline(
        embeddings=DummyEmbeddings(),
        vectorstore=DummyVectorStore(),
        llm_cloud=DummyLLM(),
        llm_fallback=DummyLLM(),
        settings=settings,
    )
    resp = pipeline.answer("hello")
    assert resp.answer == "ok"
    assert resp.sources
