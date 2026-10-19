"""Call every seed board once. Prints boards that fail, are empty, or (Greenhouse) whose name doesn't match.

Run from backend/: .venv/bin/python -m scripts.check_boards
"""

import asyncio
import re
import unicodedata

import httpx

from app.ingest.feeds import GREENHOUSE_API, LEVER_API
from app.ingest.pipeline import load_companies


def _words(name: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return set(re.findall(r"[a-z0-9]+", plain))


async def check(client: httpx.AsyncClient, c: dict) -> str | None:
    try:
        if c["ats"] == "greenhouse":
            jobs = (await client.get(f"{GREENHOUSE_API}/{c['board']}/jobs")).raise_for_status().json()["jobs"]
            name = (await client.get(f"{GREENHOUSE_API}/{c['board']}")).raise_for_status().json()["name"]
            # Board names vary ("Anduril Industries" vs "Anduril"), so any shared word counts as a match.
            if not _words(c["name"]) & _words(name):
                return f"name mismatch: board says {name!r}"
        else:
            jobs = (await client.get(f"{LEVER_API}/{c['board']}?mode=json")).raise_for_status().json()
    except (httpx.HTTPError, KeyError, ValueError) as e:
        return f"error: {type(e).__name__}"
    return None if jobs else "empty board"


async def main() -> None:
    companies = load_companies()
    async with httpx.AsyncClient(timeout=30) as client:
        problems = await asyncio.gather(*(check(client, c) for c in companies))
    for c, problem in zip(companies, problems):
        if problem:
            print(f"{c['industry']:26} {c['name']:32} {c['ats']}:{c['board']}  {problem}")
    print(f"{sum(p is None for p in problems)} of {len(companies)} boards OK")


if __name__ == "__main__":
    asyncio.run(main())
