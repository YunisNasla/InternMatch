"""Ingest schedule: Monday to Friday every 6 hours, plus a background run at startup when data is stale."""

import asyncio
import logging
from contextlib import closing
from datetime import UTC, datetime, timedelta

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app import db, llm
from app.config import settings
from app.ingest import pipeline

log = logging.getLogger(__name__)
STALE_AFTER = timedelta(hours=6)
_lock = asyncio.Lock()
_background: set[asyncio.Task] = set()  # keeps startup and manual runs from being garbage collected


def is_stale(last_finished: str | None, now: datetime | None = None) -> bool:
    if last_finished is None:
        return True
    return (now or datetime.now(UTC)) - datetime.fromisoformat(last_finished) > STALE_AFTER


async def run_ingest() -> dict | None:
    """One run, or None when a run is already going."""
    if _lock.locked():
        return None
    async with _lock:
        with closing(db.connect()) as conn:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                return await pipeline.run(conn, client, pipeline.load_companies(), llm.client())


def start_in_background() -> bool:
    """Start a run without waiting for it. False when one is already going."""
    if _lock.locked():
        return False
    task = asyncio.create_task(run_ingest())
    _background.add(task)
    task.add_done_callback(_background.discard)
    return True


def start() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.ingest_timezone)
    scheduler.add_job(
        run_ingest, CronTrigger(day_of_week="mon-fri", hour="*/6", timezone=settings.ingest_timezone),
        max_instances=1, coalesce=True,
    )
    scheduler.start()
    with closing(db.connect()) as conn:
        if is_stale(db.last_ingest(conn)):
            log.info("data is stale, starting a background ingest")
            start_in_background()
    return scheduler
