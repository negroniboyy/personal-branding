# personal-branding

Personal brand content pipeline — Notion diary → story nodes → LinkedIn drafts + Instagram reel scripts.

## Prerequisites

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- Ollama running locally (`ollama pull gemma3`)

## Quickstart

### 1. Backend

```bash
cd "NOTION DIARY FETCHER"
uv sync
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
```

API available at `http://127.0.0.1:8000` — docs at `http://127.0.0.1:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI available at `http://localhost:5173` (or `5174` if 5173 is in use).

### 3. Sync Notion diary

```bash
cd "NOTION DIARY FETCHER"
uv run sync
```

## Other commands

```bash
# Extract a reel framework from an MP4 (run from NOTION DIARY FETCHER/)
uv run python ../frameworks/instagram_frameworks/extract_reel.py \
  --file ../frameworks/instagram_frameworks/references/<file>.mp4

# Generate a reel script (run from NOTION DIARY FETCHER/)
uv run python ../frameworks/instagram_frameworks/script_writer.py \
  [--idea TEXT] [--story-id ID] [--framework-id ID]
```

## Config

All settings live in `NOTION DIARY FETCHER/config.toml`:

| Section | Controls |
|---|---|
| `[logger]` | log level, retention days |
| `[reel_extractor]` | Whisper model, Ollama model, prompts |
| `[script_writer]` | Ollama model, prompt path |
