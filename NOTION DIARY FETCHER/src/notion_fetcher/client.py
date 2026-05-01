import time
import logging
from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionClient:

    def __init__(self, token: str, rate_limit_delay: float = 0.34):
        self.client = Client(auth=token)
        self.delay = rate_limit_delay

    def _sleep(self):
        time.sleep(self.delay)

    def get_all_database_pages(self, database_id: str, page_size: int = 100) -> list[dict]:
        """Fetch ALL pages from a Notion database using cursor-based pagination."""
        pages = []
        cursor = None

        while True:
            params = {"database_id": database_id, "page_size": page_size}
            if cursor is not None:
                params["start_cursor"] = cursor

            try:
                response = self.client.databases.query(**params)
            except APIResponseError as e:
                if e.status == 429:
                    logger.warning("Rate limited by Notion, sleeping 60s")
                    time.sleep(60)
                    continue  # retry same cursor
                raise

            self._sleep()
            pages.extend(response["results"])

            if response["has_more"]:
                cursor = response["next_cursor"]
            else:
                break

        logger.info(f"Total pages fetched: {len(pages)}")
        return pages

    def get_page_blocks(self, page_id: str) -> list[dict]:
        """Fetch all block children for a page (recursive, paginated)."""
        return self._get_blocks_recursive(block_id=page_id, depth=0)

    def _get_blocks_recursive(self, block_id: str, depth: int) -> list[dict]:
        if depth > 10:
            logger.warning(f"Max recursion depth reached for block {block_id}")
            return []

        all_blocks = []
        cursor = None

        while True:
            params = {"block_id": block_id, "page_size": 100}
            if cursor is not None:
                params["start_cursor"] = cursor

            try:
                response = self.client.blocks.children.list(**params)
            except APIResponseError as e:
                if e.status == 429:
                    time.sleep(60)
                    continue
                if e.status == 404:
                    logger.warning(f"Block {block_id} not found (deleted?)")
                    return []
                raise

            self._sleep()

            for block in response["results"]:
                all_blocks.append(block)
                if block.get("has_children"):
                    children = self._get_blocks_recursive(block["id"], depth + 1)
                    all_blocks.extend(children)

            if response["has_more"]:
                cursor = response["next_cursor"]
            else:
                break

        return all_blocks