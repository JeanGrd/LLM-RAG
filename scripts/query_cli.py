from __future__ import annotations

import argparse

from rag.embeddings import OllamaEmbeddings
from rag.llm import CloudLLM, OllamaLLM
from rag.rag import RagPipeline
from rag.settings import load_settings
from rag.vectorstore import ChromaVectorStore


def build_pipeline() -> RagPipeline:
    settings = load_settings()
    return RagPipeline(
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the RAG pipeline")
    parser.add_argument("question", nargs="+", help="User question")
    args = parser.parse_args()

    question = " ".join(args.question)
    pipeline = build_pipeline()
    response = pipeline.answer(question)

    print("\nAnswer:\n")
    print(response.answer)
    print("\nSources:\n")
    for s in response.sources:
        source = s.metadata.get("source", s.doc_id)
        print(f"- {source} (score={s.score:.3f})")


if __name__ == "__main__":
    main()
