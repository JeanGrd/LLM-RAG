# Models folder

Place your downloaded `.gguf` files in this directory.

Suggested starter model for your Apple M4 Pro (fast + capable):
- `ggml-org_gemma-3-1b-it-GGUF_gemma-3-1b-it-Q4_K_M.gguf`
  - If you already pulled it with `llama-server -hf ...`, copy it from:
    `/Users/<you>/Library/Caches/llama.cpp/`

Running the server:
```bash
./scripts/run/llama_server.sh ./models/your-chat-model.gguf
# or, if only one .gguf is present in models/, just:
./scripts/run/llama_server.sh
# dedicated embedding model only:
LLAMA_EMBEDDINGS_ONLY=1 ./scripts/run/llama_server.sh ./models/embedding-model.gguf
```

Multiple models:
- llama.cpp serves one model per process. Run separate terminals/ports if you want multiple models available, then set `LLAMA_CPP_RPC_TARGETS`.
- To inspect what the project currently sees: `make models`.
