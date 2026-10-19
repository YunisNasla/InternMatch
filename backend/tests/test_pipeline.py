import json

import httpx

from app import db
from app.ingest import feeds, pipeline

ACME = [{"name": "Acme Space", "ats": "greenhouse", "board": "acme", "industry": "space"}]

SIMPLIFY_ROWS = [
    # Same job as the Acme board posting, with different location text.
    {"id": "s1", "company_name": "Acme Space", "title": "Propulsion Intern", "active": True, "is_visible": True,
     "terms": ["Summer 2027"], "locations": ["Hawthorne, California"], "date_posted": 1786000000,
     "url": "https://job-boards.greenhouse.io/acme/jobs/111?utm_source=Simplify"},
    # A non-seed company on Lever: its description is fetched from the Lever API.
    {"id": "s2", "company_name": "Rocket Lab", "title": "GNC Intern", "active": True, "is_visible": True,
     "terms": ["N/A"], "locations": ["Long Beach, CA"], "date_posted": 1786000000,
     "url": "https://jobs.lever.co/rocketlab/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
    # Title only (Workday), and closed: never stored.
    {"id": "s3", "company_name": "Analog Devices", "title": "Test Co-Op", "active": False, "is_visible": True,
     "terms": ["Summer 2027"], "locations": ["Wilmington, MA"], "date_posted": 1786000000,
     "url": "https://analogdevices.wd1.myworkdayjobs.com/x"},
    # Out-of-cycle term: dropped.
    {"id": "s4", "company_name": "Old Co", "title": "Intern", "active": True, "is_visible": True,
     "terms": ["Summer 2026"], "locations": ["Austin, TX"], "date_posted": 1786000000, "url": "https://example.com"},
]

ACME_JOBS = {"jobs": [
    {"id": 111, "title": "Propulsion Intern", "location": {"name": "Hawthorne, CA"},
     "absolute_url": "https://boards.greenhouse.io/acme/jobs/111", "first_published": "2026-07-21T19:49:28-04:00",
     "updated_at": "2026-10-14T17:51:29-04:00", "content": "&lt;p&gt;Hot fire testing, Summer 2027.&lt;/p&gt;"},
    {"id": 222, "title": "Senior Engineer", "location": {"name": "Hawthorne, CA"},
     "absolute_url": "https://boards.greenhouse.io/acme/jobs/222", "first_published": None,
     "updated_at": "2026-10-14T17:51:29-04:00", "content": ""},
]}

LEVER_JOB = {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "text": "GNC Intern", "workplaceType": "remote",
             "descriptionPlain": "Write guidance code.", "lists": [{"text": "Requirements", "content": "<li>C++</li>"}]}


def transport(board_up=True):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == feeds.SIMPLIFY_URL:
            return httpx.Response(200, json=SIMPLIFY_ROWS)
        if "/boards/acme/jobs" in url:
            return httpx.Response(200, json=ACME_JOBS) if board_up else httpx.Response(503)
        if "api.lever.co/v0/postings/rocketlab/" in url:
            return httpx.Response(200, json=LEVER_JOB)
        return httpx.Response(404)
    return httpx.MockTransport(handler)


async def ingest(conn, board_up=True, companies=ACME):
    async with httpx.AsyncClient(transport=transport(board_up)) as client:
        return await pipeline.run(conn, client, companies)


def rows(conn):
    return {r["id"]: r for r in conn.execute("SELECT * FROM postings")}


async def test_first_run_merges_fetches_and_filters(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    counts = await ingest(conn)
    postings = rows(conn)

    assert set(postings) == {"greenhouse:acme:111", "lever:rocketlab:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}
    acme = postings["greenhouse:acme:111"]
    assert json.loads(acme["sources"]) == ["greenhouse:acme", "simplify"]
    assert json.loads(acme["terms"]) == ["Summer 2027"]
    assert (acme["posted_at"], acme["date_kind"]) == ("2026-07-21T23:49:28Z", "posted")
    rocket = postings["lever:rocketlab:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]
    assert rocket["description"] == "Write guidance code.\nRequirements\nC++"
    assert rocket["work_arrangement"] == "remote"
    assert json.loads(rocket["terms"]) == ["unknown"]
    assert counts["feeds_failed"] == 0
    assert conn.execute("SELECT industry FROM companies WHERE name = 'Acme Space'").fetchone()[0] == "space"
    assert db.last_ingest(conn) is not None


async def test_failed_board_leaves_postings_open_and_dropped_board_closes_them(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    await ingest(conn)
    SIMPLIFY_ROWS[0]["active"] = False  # Simplify closes the Acme job
    try:
        await ingest(conn, board_up=False)
        assert rows(conn)["greenhouse:acme:111"]["active"] == 1  # board failed: unchanged
        await ingest(conn, companies=[])
        assert rows(conn)["greenhouse:acme:111"]["active"] == 0  # board removed from the yaml: closed
    finally:
        SIMPLIFY_ROWS[0]["active"] = True
