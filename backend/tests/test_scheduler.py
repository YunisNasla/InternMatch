import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.ingest import pipeline, scheduler
from app.main import app

NOW = datetime(2026, 10, 19, 18, 0, tzinfo=UTC)


def test_staleness():
    assert scheduler.is_stale(None, NOW)
    assert not scheduler.is_stale("2026-10-19T13:00:00Z", NOW)
    assert scheduler.is_stale("2026-10-19T11:59:00Z", NOW)


async def test_second_run_is_refused_while_one_is_going(monkeypatch):
    release = asyncio.Event()

    async def slow_run(*args):
        await release.wait()
        return {"kept": 0}

    monkeypatch.setattr(pipeline, "run", slow_run)
    first = asyncio.create_task(scheduler.run_ingest())
    await asyncio.sleep(0)
    assert await scheduler.run_ingest() is None
    assert scheduler.start_in_background() is False
    release.set()
    assert await first == {"kept": 0}


def test_ingest_route_is_off_by_default():
    assert TestClient(app).post("/api/ingest").status_code in (404, 405)
