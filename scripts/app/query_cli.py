from __future__ import annotations

import argparse

from rag.runtime import build_pipeline


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
