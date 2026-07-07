"""HTTP surface for Notion ideas sync — thin enqueue wrapper, no business logic."""

from fastapi import APIRouter

from jobs import queue as jobs_queue

router = APIRouter(prefix="/notion", tags=["notion"])


@router.post("/sync")
def sync_ideas():
    job_id = jobs_queue.enqueue("sync_notion_ideas", {})
    return {"job_id": job_id}
