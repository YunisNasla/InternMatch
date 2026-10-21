"""Bare prompt vs persona + chain-of-thought (Prompts 2 + 3), against hand labels.

Run from backend/: PYTHONPATH=. .venv/bin/python ../eval/run_eval.py
Needs eval/labels.json: a list of 10 tiers, in the order of eval/postings.json.
Calls Claude directly (about 60 Haiku calls, a few cents) and never touches the score cache.
"""

import asyncio
import json
import re
from pathlib import Path

from app import llm
from app.llm import HAIKU, load_prompt
from app.matching import cache, scorer
from app.schemas import Profile, tier_for

EVAL = Path(__file__).parent
RUNS = 3


async def bare_score(client, profile_json: str, row: dict) -> int | None:
    """The first integer in the reply, or None when the reply holds no 0 to 100 score (a format failure)."""
    user = load_prompt(
        "scorer_user.txt", profile_json_without_location=profile_json, company=row["company"], title=row["title"],
        industry=row["industry"] or "other", role_type=row["role_type"] or "unknown", terms=", ".join(row["terms"]),
        description_text=row["description"],
    )
    response = await client.messages.create(
        model=HAIKU, system=(EVAL / "bare_prompt.txt").read_text(), messages=[{"role": "user", "content": user}],
        max_tokens=2000, output_config={"effort": cache.SCORER_EFFORT},
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    found = re.search(r"\d+", text)
    return int(found[0]) if found and int(found[0]) <= 100 else None


async def main() -> None:
    profile = Profile.model_validate_json((EVAL / "profile.json").read_text())
    postings = json.loads((EVAL / "postings.json").read_text())
    labels = json.loads((EVAL / "labels.json").read_text())
    assert len(labels) == len(postings) and set(labels) <= {"strong", "good", "stretch", "long_shot"}
    client = llm.client()
    profile_json = profile.model_dump_json(exclude={"location"}, indent=1)
    sem = asyncio.Semaphore(10)

    gaps = {}  # posting index -> the scorer's key gaps from one run, to explain its scores

    async def run(kind: str, i: int) -> int | None:
        async with sem:
            if kind == "bare":
                return await bare_score(client, profile_json, postings[i])
            result = await scorer._score_one(client, profile_json, postings[i], None)
            gaps.setdefault(i, result.key_gaps)
            return result.fit_score

    jobs = [(kind, i) for kind in ("bare", "persona_cot") for i in range(len(postings)) for _ in range(RUNS)]
    scores = await asyncio.gather(*(run(kind, i) for kind, i in jobs))
    by = {"bare": [[] for _ in postings], "persona_cot": [[] for _ in postings]}
    for (kind, i), s in zip(jobs, scores):
        by[kind][i].append(s)

    results = {"labels": labels, "postings": [f"{p['company']}: {p['title']}" for p in postings]}
    for kind, runs in by.items():
        valid = [[s for s in r if s is not None] for r in runs]
        tiers = [tier_for(v[0]) if v else None for v in valid]
        spreads = [max(v) - min(v) for v in valid if v]
        results[kind] = {
            "scores": runs,
            "first_run_tiers": tiers,
            "tier_matches": sum(t == lab for t, lab in zip(tiers, labels)),
            "mean_spread": round(sum(spreads) / len(spreads), 1),
            "max_spread": max(spreads),
            "invalid_replies": sum(s is None for r in runs for s in r),
        }
    results["persona_cot"]["key_gaps"] = [gaps[i] for i in range(len(postings))]
    (EVAL / "results.json").write_text(json.dumps(results, indent=1))
    for kind in by:
        r = results[kind]
        print(f"{kind}: {r['tier_matches']}/10 tiers match, mean spread {r['mean_spread']}, max spread {r['max_spread']}, {r['invalid_replies']} invalid replies")


if __name__ == "__main__":
    asyncio.run(main())
