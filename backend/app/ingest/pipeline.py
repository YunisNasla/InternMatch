"""One ingest run: ARCHITECTURE.md "Ingest and tagging", steps 1 to 8."""

import asyncio
import json
import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

import anthropic
import httpx
import yaml

from app.config import REPO_ROOT
from app.ingest import feeds, rules, taggers
from app.llm import LLMError
from app.taxonomy import SUPPORTED_TERMS

log = logging.getLogger(__name__)
COMPANIES_FILE = REPO_ROOT / "backend/data/companies.yaml"
KEEP_TERMS = set(SUPPORTED_TERMS) | set(rules.UNKNOWN_TERMS)


def load_companies() -> list[dict]:
    """Seed companies as dicts with name, ats, board and industry."""
    if not COMPANIES_FILE.exists():
        return []
    data = yaml.safe_load(COMPANIES_FILE.read_text()) or {}
    return [{**c, "industry": industry} for industry, companies in data.items() for c in companies or []]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def run(
    conn: sqlite3.Connection, client: httpx.AsyncClient, companies: list[dict], llm: anthropic.AsyncAnthropic,
) -> dict:
    started = _now()
    run_id = conn.execute("INSERT INTO ingest_runs (started_at) VALUES (?)", (started,)).lastrowid
    conn.commit()
    sem = asyncio.Semaphore(10)

    async def limited(coro):
        async with sem:
            return await coro

    # 1. Pull every feed, recording which succeeded.
    pulls = {"simplify": feeds.fetch_simplify(client)}
    for c in companies:
        pulls[f"{c['ats']}:{c['board']}"] = feeds.fetch_board(client, c["ats"], c["board"], c["name"])
    results = dict(zip(pulls, await asyncio.gather(*(limited(p) for p in pulls.values()), return_exceptions=True)))
    ok_feeds = {feed for feed, r in results.items() if not isinstance(r, BaseException)}
    errors = {feed: type(r).__name__ for feed, r in results.items() if isinstance(r, BaseException)}
    tag_failures = 0

    # 2. Internships only on boards, read their terms, keep supported terms plus unknown, drop non-US jobs.
    postings = []
    for feed in ok_feeds:
        for p in results[feed]:
            if feed != "simplify":
                if not rules.is_internship(p.title):
                    continue
                p.terms = rules.extract_terms(p.title, p.description)
                p.degree_levels = rules.degree_levels(None, p.title)
            if KEEP_TERMS & set(p.terms) and not rules.is_non_us(p.locations):
                postings.append(p)

    # 3. Drop duplicates, and anything already dropped as non_stem.
    dropped = {r[0] for r in conn.execute("SELECT id FROM dropped")}
    postings = [p for p in rules.dedupe(postings) if p.id not in dropped]

    # 4. Pull descriptions for new Simplify postings that link to Greenhouse or Lever.
    has_text = {r[0] for r in conn.execute("SELECT id FROM postings WHERE has_description = 1")}
    need = [p for p in postings if p.ats_job_id and not p.description and p.id not in has_text]
    fetched = await asyncio.gather(
        *(limited(feeds.fetch_description(client, p.ats, p.board, p.ats_job_id)) for p in need),
        return_exceptions=True,
    )
    for p, result in zip(need, fetched):
        if not isinstance(result, BaseException):
            p.description, p.lever_workplace = result
    # A posting whose tag call failed last run is tagged again from its stored description, not just its title.
    retry = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT id, description, lever_workplace FROM postings WHERE role_type IS NULL AND has_description = 1"
    )}
    for p in postings:
        if p.id in retry and not p.description:
            p.description, p.lever_workplace = retry[p.id]

    # 5. Tag each new posting once. non_stem postings are dropped for good; failed calls retry next run.
    tagged = {r[0] for r in conn.execute("SELECT id FROM postings WHERE role_type IS NOT NULL")}
    tags: dict[str, object] = {}
    new = [p for p in postings if p.id not in tagged]
    results = await asyncio.gather(*(limited(taggers.tag_posting(llm, p)) for p in new), return_exceptions=True)
    for p, result in zip(new, results):
        if isinstance(result, LLMError | anthropic.APIError):
            errors[p.id] = type(result).__name__
            tag_failures += 1
        elif isinstance(result, BaseException):
            raise result
        else:
            tags[p.id] = result
    non_stem = {pid for pid, t in tags.items() if t.role_type == "non_stem"}
    conn.executemany("INSERT OR IGNORE INTO dropped (id) VALUES (?)", [(pid,) for pid in non_stem])
    postings = [p for p in postings if p.id not in non_stem]

    # 6. Seed companies take their list's industry; other new companies are tagged once.
    conn.executemany(
        "INSERT INTO companies (name, industry, industry_source, ats, board) VALUES (?, ?, 'seed_list', ?, ?) "
        "ON CONFLICT(name) DO UPDATE SET industry = excluded.industry, industry_source = 'seed_list', "
        "ats = excluded.ats, board = excluded.board",
        [(c["name"], c["industry"], c["ats"], c["board"]) for c in companies],
    )
    conn.executemany("INSERT OR IGNORE INTO companies (name) VALUES (?)", [(p.company,) for p in postings])
    conn.commit()  # no write transaction stays open while the company tagger waits on the API
    untagged = {r[0] for r in conn.execute("SELECT name FROM companies WHERE industry IS NULL")}
    titles: dict[str, list[str]] = {}
    for p in postings:
        if p.company in untagged:
            titles.setdefault(p.company, []).append(p.title)
    results = await asyncio.gather(
        *(limited(taggers.tag_company(llm, name, t)) for name, t in titles.items()), return_exceptions=True,
    )
    for name, result in zip(titles, results):
        if isinstance(result, LLMError | anthropic.APIError):
            errors[f"company:{name}"] = type(result).__name__
            tag_failures += 1
        elif isinstance(result, BaseException):
            raise result
        else:
            conn.execute(
                "UPDATE companies SET industry = ?, industry_source = 'tagger', confidence = ? WHERE name = ?",
                (result.industry, result.confidence, name),
            )

    # 7. Save. Existing rows keep first_seen, tags and every source they ever had.
    now = _now()
    stored = {r["id"]: set(json.loads(r["sources"])) for r in conn.execute("SELECT id, sources FROM postings")}
    conn.executemany(
        """INSERT INTO postings (id, source, company, title, locations, terms, url, ats_job_id, posted_at, date_kind,
               description, has_description, lever_workplace, degree_levels, role_type, work_arrangement, active,
               sources, first_seen, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET company = excluded.company, title = excluded.title,
               locations = excluded.locations,
               terms = excluded.terms, url = excluded.url, posted_at = excluded.posted_at,
               date_kind = excluded.date_kind, sources = excluded.sources, degree_levels = excluded.degree_levels,
               description = COALESCE(excluded.description, postings.description),
               has_description = MAX(excluded.has_description, postings.has_description),
               role_type = COALESCE(excluded.role_type, postings.role_type),
               work_arrangement = CASE WHEN excluded.role_type IS NULL THEN postings.work_arrangement
                                       ELSE excluded.work_arrangement END""",
        [
            (p.id, p.ats or "simplify", p.company, p.title, json.dumps(p.locations), json.dumps(p.terms), p.url,
             p.ats_job_id, p.posted_at, p.date_kind, p.description, int(bool(p.description)), p.lever_workplace,
             json.dumps(p.degree_levels), tags[p.id].role_type if p.id in tags else None,
             # Title-only postings ignore the tagger's arrangement: it only saw the title.
             rules.arrangement(
                 p.lever_workplace, tags[p.id].work_arrangement if p.id in tags and p.description else None, p.locations,
             ),
             json.dumps(sorted(stored.get(p.id, set()) | p.sources)), now, now)
            for p in postings
        ],
    )

    # 8. Open, close or leave each posting (ARCHITECTURE ingest step 8).
    seen = {p.id: p.sources for p in postings}
    known_feeds = {"simplify"} | {f"{c['ats']}:{c['board']}" for c in companies}
    updates = []
    for r in conn.execute("SELECT id, active, sources FROM postings"):
        open_feeds = seen.get(r["id"], set())
        active = rules.next_active(bool(r["active"]), set(json.loads(r["sources"])), open_feeds, ok_feeds, known_feeds)
        updates.append((int(active), now if open_feeds else None, r["id"]))
    conn.executemany("UPDATE postings SET active = ?, last_seen = COALESCE(?, last_seen) WHERE id = ?", updates)

    counts = {
        "feeds_ok": len(ok_feeds), "feeds_failed": len(pulls) - len(ok_feeds), "tag_failures": tag_failures,
        "kept": len(postings),
        "descriptions_fetched": sum(1 for p in need if p.description), "tagged": len(tags),
        "active": conn.execute("SELECT COUNT(*) FROM postings WHERE active = 1").fetchone()[0],
    }
    conn.execute(
        "UPDATE ingest_runs SET finished_at = ?, counts = ?, errors = ? WHERE id = ?",
        (_now(), json.dumps(counts), json.dumps(errors) if errors else None, run_id),
    )
    conn.commit()
    log.info("ingest finished: %s", counts)
    return counts


async def main() -> None:
    from app import db, llm

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        with closing(db.connect()) as conn:
            print(await run(conn, client, load_companies(), llm.client()))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(main())
