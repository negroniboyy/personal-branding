# personal-branding

Personal brand content pipeline — Notion ideas → LinkedIn drafts + Instagram reel scripts, voice-matched and production-tiered.

## Prerequisites

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- An OpenRouter API key (all generation runs through OpenRouter — no local model runtime required)
- A Notion integration token (for the Ideas DB sync)

Copy `NOTION DIARY FETCHER/.env.example` to `NOTION DIARY FETCHER/.env` and fill in `NOTION_TOKEN` and `OPENROUTER_API_KEY`.

## Quickstart

### Option A — one command (macOS)

```bash
./start.sh
```

Opens two Terminal tabs: the frontend (`5173`) and the unified API (`9000`, with `--reload`).

### Option B — manual, two terminals

**1. Backend**

```bash
cd "NOTION DIARY FETCHER"
uv sync
uv run uvicorn api.main:app --host 127.0.0.1 --port 9000 --reload
```

API available at `http://127.0.0.1:9000` — docs at `http://127.0.0.1:9000/docs`.

**2. Frontend**

```bash
cd frontend
npm install
npm run dev
```

UI available at `http://localhost:5173` (or `5174` if `5173` is in use).

## Using the app

- **Studio** — the lifecycle queue: review, approve/kill, caption, and post generated drafts.
- **Ideas** — the primary surface. Drop an idea, generate a LinkedIn draft or reel script from it, iterate.
- **Writer** / **Reels** — standalone idea-prompt-driven generation (pick a framework, write an idea hint, generate).
- **Frameworks** — browse extracted LinkedIn/reel frameworks.

## Other commands

```bash
# Extract a reel framework from an MP4 (run from NOTION DIARY FETCHER/)
uv run python ../frameworks/instagram_frameworks/extract_reel.py \
  --file ../frameworks/instagram_frameworks/references/<file>.mp4
```

Reel/LinkedIn script generation is idea-driven only and happens through the app (Ideas/Writer/Reels tabs) — there is no longer a standalone CLI for it.

## Config

All settings live in `NOTION DIARY FETCHER/config.toml`:

| Section | Controls |
|---|---|
| `[logger]` | log level, retention days |
| `[reel_extractor]` | Whisper model, scene-detect mode, min transcript length |
| `[content_writer]` | provider, recognized content domains |
| `[script_writer]` | provider |

Model routing (which OpenRouter models per task, in priority order) lives in `config/openrouter_models.yaml`, not in `config.toml`.
