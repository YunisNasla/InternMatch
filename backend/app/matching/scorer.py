"""Prompts 2 + 3: the recruiter scorer (Persona + Chain-of-thought), with the score cache in front."""

import asyncio
import logging
import sqlite3

import anthropic

from app.llm import HAIKU, LLMError, call_json, load_prompt
from app.matching import cache
from app.schemas import Profile, ScoreResult
from app.taxonomy import recruiter_domain

log = logging.getLogger(__name__)
MAX_DESCRIPTION = 6000
PARALLEL = 20  # a whole first page at once: each call takes about 15 s


async def _score_one(llm: anthropic.AsyncAnthropic, profile_json: str, row: dict, emphasis: str | None) -> ScoreResult:
    emphasis_block = load_prompt("scorer_emphasis.txt", emphasis=emphasis).strip() if emphasis else ""
    system = load_prompt(
        "scorer_system.txt", recruiter_domain=recruiter_domain(row["role_type"], row["industry"]),
        emphasis_block=emphasis_block,
    )
    user = load_prompt(
        "scorer_user.txt", profile_json_without_location=profile_json, company=row["company"], title=row["title"],
        industry=row["industry"] or "other", role_type=row["role_type"] or "unknown", terms=", ".join(row["terms"]),
        description_text=row["description"][:MAX_DESCRIPTION],
    )
    return await call_json(llm, HAIKU, system, user, ScoreResult, label=row["id"], effort=cache.SCORER_EFFORT, max_tokens=8000)


async def score(
    llm: anthropic.AsyncAnthropic, conn: sqlite3.Connection, profile: Profile, rows: list[dict], emphasis: str | None,
) -> tuple[dict[str, ScoreResult], list[str]]:
    """({job id: result}, job ids that couldn't be scored). Cached results are reused, new ones are saved."""
    if any(not r["has_description"] for r in rows):
        raise ValueError("title-only postings are never scored")
    ph, version = cache.profile_hash(profile), cache.prompt_version()
    profile_json = profile.model_dump_json(exclude={"location"}, indent=1)
    results = {r["id"]: hit for r in rows if (hit := cache.get(conn, ph, r["id"], emphasis, version))}
    misses = [r for r in rows if r["id"] not in results]
    sem = asyncio.Semaphore(PARALLEL)

    async def limited(row: dict) -> ScoreResult:
        async with sem:
            return await _score_one(llm, profile_json, row, emphasis)

    unscored = []
    for row, result in zip(misses, await asyncio.gather(*map(limited, misses), return_exceptions=True)):
        if isinstance(result, ScoreResult):
            cache.put(conn, ph, row["id"], emphasis, version, result)
            results[row["id"]] = result
        elif isinstance(result, LLMError | anthropic.APIError):
            log.warning("score failed for %s: %s", row["id"], type(result).__name__)
            if old := cache.fallback(conn, ph, row["id"]):
                results[row["id"]] = old
            else:
                unscored.append(row["id"])
        else:
            raise result
    log.info("scored %s postings: %s cached, %s new, %s unscored", len(rows), len(rows) - len(misses),
             len(misses) - len(unscored), len(unscored))
    return results, unscored
