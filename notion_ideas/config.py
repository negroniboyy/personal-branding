"""Env access for the Notion ideas sync. Same .env file and load pattern as
openrouter/client.py — reused, not duplicated logic."""

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / "NOTION DIARY FETCHER" / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


class ConfigError(RuntimeError):
    pass


def get_notion_token() -> str:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ConfigError(f"NOTION_TOKEN not set — add it to {_ENV_PATH}")
    return token


def get_ideas_database_id() -> str:
    db_id = os.environ.get("NOTION_IDEAS_DATABASE_ID")
    if not db_id:
        raise ConfigError(
            f"NOTION_IDEAS_DATABASE_ID not set — add it to {_ENV_PATH} "
            "(see handoff/blueprint_v3.2_notion_ideas_sync.md)"
        )
    return db_id
