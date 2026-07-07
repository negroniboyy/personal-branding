from typing import Optional

from fastapi import APIRouter, HTTPException

from . import queue as jobs_queue

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str):
    job = jobs_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id!r} not found")
    return job


@router.get("")
def list_jobs(status: Optional[str] = None, kind: Optional[str] = None, limit: int = 100):
    return jobs_queue.list_jobs(status=status, kind=kind, limit=limit)
