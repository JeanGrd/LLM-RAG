# Data Layout

```
data/
  raw/        # input source files for ingestion
  processed/  # optional preprocessed outputs
  indices/    # vector store persistence
```

## Supported file types
- PDF (`.pdf`)
- Markdown (`.md`, `.markdown`)
- HTML/XML (`.html`, `.htm`, `.xml`)
- JSON (`.json`, `.jsonl`, `.ndjson`)
- YAML (`.yaml`, `.yml`)
- Text-like (`.txt`, `.log`, `.cfg`, `.conf`, `.ini`, `.toml`, `.csv`, `.tsv`, `.rst`)

## Tips
- Keep each document in a separate file for clearer source attribution.
- Use consistent filenames and directories to make source tracing easier.
- After changing files in `data/raw`, run ingestion again to refresh the index.
