# Notion Diary Fetcher

Syncs diary entries from Notion database to local Markdown files.

## Setup

```bash
uv sync
cp .env.example .env
# Edit .env with your Notion API token and database ID
```

## Run

```bash
uv run python main.py
```

## Config

Edit `config.toml` to customize sync behavior.