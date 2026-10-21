"""Adapters for the three job sources. Each turns one feed into RawPostings and raises on HTTP errors."""

import httpx

from app.ingest.rules import (
    UNKNOWN_TERMS,
    RawPosting,
    ats_job_id_from_url,
    degree_levels,
    pick_date,
    strip_html,
)

SIMPLIFY_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json"
GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards"
LEVER_API = "https://api.lever.co/v0/postings"


async def _json(client: httpx.AsyncClient, url: str):
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def fetch_simplify(client: httpx.AsyncClient) -> list[RawPosting]:
    """Only rows Simplify still lists as open."""
    postings = []
    for row in await _json(client, SIMPLIFY_URL):
        if not (row.get("active") and row.get("is_visible", True)):
            continue
        ats = ats_job_id_from_url(row["url"])
        terms = [t for t in row.get("terms", []) if t and t != "N/A"] or list(UNKNOWN_TERMS)
        posted_at, date_kind = pick_date(row.get("date_posted"), row.get("date_updated"))
        postings.append(RawPosting(
            feed="simplify", source_id=row["id"], company=row["company_name"], title=row["title"],
            locations=row.get("locations", []), terms=terms, url=row["url"],
            posted_at=posted_at, date_kind=date_kind,
            ats=ats and ats[0], board=ats and ats[1], ats_job_id=ats and ats[2],
            degree_levels=degree_levels(row.get("degrees"), row["title"]),
        ))
    return postings


def _lever_description(job: dict) -> str:
    parts = [job.get("descriptionPlain", "")]
    for section in job.get("lists", []):
        parts += [section.get("text", ""), strip_html(section.get("content", ""))]
    parts.append(job.get("additionalPlain", ""))
    return "\n".join(p.strip() for p in parts if p and p.strip())


def _board_posting(ats: str, board: str, company: str, job: dict) -> RawPosting:
    if ats == "greenhouse":
        posted_at, date_kind = pick_date(job.get("first_published"), job.get("updated_at"))
        location = (job.get("location") or {}).get("name")
        return RawPosting(
            feed=f"greenhouse:{board}", source_id=str(job["id"]), company=company, title=job["title"],
            locations=[location] if location else [], terms=[], url=job["absolute_url"],
            posted_at=posted_at, date_kind=date_kind, ats="greenhouse", board=board, ats_job_id=str(job["id"]),
            description=strip_html(job.get("content", "")) or None,
        )
    categories = job.get("categories", {})
    created = job.get("createdAt")
    posted_at, date_kind = pick_date(created / 1000 if created else None, None)
    return RawPosting(
        feed=f"lever:{board}", source_id=job["id"], company=company, title=job["text"],
        locations=categories.get("allLocations") or [l for l in [categories.get("location")] if l],
        terms=[], url=job["hostedUrl"], posted_at=posted_at, date_kind=date_kind,
        ats="lever", board=board, ats_job_id=job["id"],
        description=_lever_description(job) or None, lever_workplace=job.get("workplaceType"),
    )


async def fetch_board(client: httpx.AsyncClient, ats: str, board: str, company: str) -> list[RawPosting]:
    """Every job on a seed-list board. The pipeline keeps only internships."""
    if ats == "greenhouse":
        jobs = (await _json(client, f"{GREENHOUSE_API}/{board}/jobs?content=true"))["jobs"]
    else:
        jobs = await _json(client, f"{LEVER_API}/{board}?mode=json")
    return [_board_posting(ats, board, company, job) for job in jobs]


async def fetch_description(client: httpx.AsyncClient, ats: str, board: str, job_id: str) -> tuple[str | None, str | None]:
    """(description, Lever workplaceType) for one job behind a Simplify apply link."""
    if ats == "greenhouse":
        job = await _json(client, f"{GREENHOUSE_API}/{board}/jobs/{job_id}")
        return strip_html(job.get("content", "")) or None, None
    job = await _json(client, f"{LEVER_API}/{board}/{job_id}")
    return _lever_description(job) or None, job.get("workplaceType")
