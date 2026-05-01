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