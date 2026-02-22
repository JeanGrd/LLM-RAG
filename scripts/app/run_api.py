from __future__ import annotations

from rag.settings import load_settings

import uvicorn


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "rag.api.app:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
    )


if __name__ == "__main__":
    main()
