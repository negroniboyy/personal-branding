# Blueprint v1.0 — Part 1/4: Spec + Scaffold
# Notion Diary → SQLite Sync

**Feed order:** p1 → p2 → p3 → p4
**Execution target:** Gemma4 (e2b)

---

## STATE — Files to Create

Do NOT modify: `CLAUDE.md`, `CONTINUE.md`

Create all of the following from scratch:
```
pyproject.toml
.env.example
config.toml
.gitignore
main.py
src/notion_fetcher/__init__.py   (empty file)
src/notion_fetcher/client.py     (see Part 2)
src/notion_fetcher/database.py   (see Part 3)
src/notion_fetcher/chunker.py    (see Part 4)
src/notion_fetcher/sync.py       (see Part 4)
```

---

## SPECS

- Python 3.12, uv package manager
- pyproject.toml only — NO requirements.txt
- sqlite3 (stdlib) — no SQLAlchemy
- tomllib (stdlib, Python 3.11+) for config.toml
- python-dotenv for .env
- notion-client (official PyPI SDK)

---

## FILE: pyproject.toml

```toml
[project]
name = "notion-fetcher"
version = "0.1.0"
description = "Fetches Notion diary database and stores in SQLite"
requires-python = ">=3.12"
dependencies = [
    "notion-client>=2.2.1",
    "python-dotenv>=1.0.0",
]

[project.scripts]
sync = "notion_fetcher.sync:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/notion_fetcher"]
```

---

## FILE: .env.example

```
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## FILE: config.toml

```toml
[database]
path = "data/notion_diary.db"

[sync]
rate_limit_delay = 0.34
chunk_size_tokens = 500
chunk_overlap_chars = 50

[notion]
page_size = 100
```

---

## FILE: .gitignore

```
.env
*.db
*.sqlite
__pycache__/
.venv/
dist/
.DS_Store
```

---

## FILE: main.py

```python
import os
import sys
import tomllib
from pathlib import Path
from dotenv import load_dotenv


def main():
    load_dotenv()

    config_path = Path("config.toml")
    if not config_path.exists():
        print("ERROR: config.toml not found")
        sys.exit(1)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    if not token or not database_id:
        print("ERROR: NOTION_TOKEN and NOTION_DATABASE_ID must be set in .env")
        sys.exit(1)

    from notion_fetcher.sync import run_sync
    run_sync(token=token, database_id=database_id, config=config)


if __name__ == "__main__":
    main()
```

---

## DONE FOR PART 1

After creating all files above, feed Part 2 (client.py).
