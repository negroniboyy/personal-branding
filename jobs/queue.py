"""Background job queue.

Interface: enqueue() to submit work, get_job()/list_jobs() to poll status,
register() to wire up a handler for a job kind. Persistence, the worker
thread, and crash recovery are internal — callers never touch them directly.

A job is queued -> running -> done|failed. Handlers are plain functions
(payload dict in, JSON-serializable result dict out) executed one at a time
on a single background thread, so callers (and the UI) can leave and come
back without losing in-flight work.
"""

import json
import queue as _queue
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from shared.logger import get_logger

logger = get_logger("jobs")

_REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "data" / "notion_diary.db"

_MIGRATION = """
CREATE TABLE IF NOT EXISTS jobs (
    id           TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'queued',
    result_json  TEXT,
    error        TEXT,
    created_at   TEXT NOT NULL,
    started_at   TEXT,
    finished_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_kind ON jobs(kind);
"""

_handlers: dict[str, Callable[[dict], dict]] = {}
_pending: "_queue.Queue[str]" = _queue.Queue()
_worker_lock = threading.Lock()
_worker_started = False


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_migration() -> None:
    conn = _db()
    try:
        conn.executescript(_MIGRATION)
        conn.commit()
    finally:
        conn.close()


def register(kind: str, handler: Callable[[dict], dict]) -> None:
    """Wire a handler for a job kind. Call at import time, before the app starts."""
    _handlers[kind] = handler


def enqueue(kind: str, payload: dict) -> str:
    if kind not in _handlers:
        raise ValueError(f"no handler registered for job kind {kind!r}")
    job_id = uuid.uuid4().hex[:12]
    conn = _db()
    try:
        conn.execute(
            "INSERT INTO jobs (id, kind, payload_json, status, created_at) VALUES (?, ?, ?, 'queued', ?)",
            (job_id, kind, json.dumps(payload), _now()),
        )
        conn.commit()
    finally:
        conn.close()
    start_worker()
    _pending.put(job_id)
    return job_id


def get_job(job_id: str) -> Optional[dict]:
    conn = _db()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def list_jobs(status: Optional[str] = None, kind: Optional[str] = None, limit: int = 100) -> list[dict]:
    conn = _db()
    try:
        where, params = [], []
        if status:
            where.append("status = ?")
            params.append(status)
        if kind:
            where.append("kind = ?")
            params.append(kind)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params.append(limit)
        rows = conn.execute(
            f"SELECT * FROM jobs {clause} ORDER BY created_at DESC LIMIT ?", params
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def recover_stale_jobs() -> int:
    """Mark jobs stuck in 'running' from a crashed/killed process as failed. Call once at startup."""
    conn = _db()
    try:
        cur = conn.execute(
            "UPDATE jobs SET status = 'failed', error = 'interrupted by server restart', finished_at = ? "
            "WHERE status = 'running'",
            (_now(),),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def start_worker() -> None:
    """Idempotent — safe to call from multiple places (app startup, enqueue)."""
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True
        threading.Thread(target=_worker_loop, daemon=True, name="jobs-worker").start()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["payload"] = json.loads(d.pop("payload_json") or "{}")
    result_json = d.pop("result_json")
    d["result"] = json.loads(result_json) if result_json else None
    return d


def _worker_loop() -> None:
    # Pick up anything left 'queued' from a previous process (e.g. a restart
    # landing between insert and the in-memory _pending.put).
    conn = _db()
    try:
        rows = conn.execute(
            "SELECT id FROM jobs WHERE status = 'queued' ORDER BY created_at"
        ).fetchall()
        for row in rows:
            _pending.put(row["id"])
    finally:
        conn.close()

    while True:
        job_id = _pending.get()
        _run_job(job_id)


def _run_job(job_id: str) -> None:
    conn = _db()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row or row["status"] != "queued":
            return
        kind = row["kind"]
        payload = json.loads(row["payload_json"] or "{}")
        conn.execute(
            "UPDATE jobs SET status = 'running', started_at = ? WHERE id = ?", (_now(), job_id)
        )
        conn.commit()
    finally:
        conn.close()

    try:
        handler = _handlers.get(kind)
        if handler is None:
            raise RuntimeError(f"no handler registered for job kind {kind!r}")
        result = handler(payload)
        conn = _db()
        try:
            conn.execute(
                "UPDATE jobs SET status = 'done', result_json = ?, finished_at = ? WHERE id = ?",
                (json.dumps(result), _now(), job_id),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("job %s (%s) failed: %s", job_id, kind, exc)
        conn = _db()
        try:
            conn.execute(
                "UPDATE jobs SET status = 'failed', error = ?, finished_at = ? WHERE id = ?",
                (str(exc), _now(), job_id),
            )
            conn.commit()
        finally:
            conn.close()
