"""Pick 10 postings for the evaluation and write the labeling sheet.

Run once from backend/: PYTHONPATH=. .venv/bin/python ../eval/make_sheet.py
The fixture profile (eval/profile.json) is a made-up mechanical engineering student.
"""

import json
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from app import db
from app.llm import MAX_DESCRIPTION
from app.matching import filters, prefilter
from app.schemas import FilterState, Profile

EVAL = Path(__file__).parent
# Ranks spread from the closest TF-IDF match to clear mismatches, so the labels span all four tiers.
RANKS = [0, 1, 3, 7, 15, 30, 60, 120, 250, 500]
FIELDS = ("id", "company", "title", "industry", "role_type", "terms", "url")


def main() -> None:
    profile = Profile.model_validate_json((EVAL / "profile.json").read_text())
    with closing(db.connect()) as conn:
        rows, _ = filters.hard_filter(filters.load_active(conn), FilterState(terms=["Summer 2027", "Fall 2026", "Spring 2027"]),
                                      datetime.now(UTC))
    ranked = prefilter.rank(profile, rows)
    picked = [ranked[i] for i in RANKS]
    postings = [{k: r[k] for k in FIELDS} | {"description": r["description"][:MAX_DESCRIPTION]} for r in picked]
    (EVAL / "postings.json").write_text(json.dumps(postings, indent=1))

    edu = profile.education[0]
    skills = "; ".join(f"{k.replace('_', ' ')}: {', '.join(v)}" for k, v in profile.skills.model_dump().items() if v)
    lines = [
        "# Evaluation label sheet",
        "",
        "Label how competitive this student would be for each posting, the way an honest recruiter would.",
        "Pick one tier per posting: **strong**, **good**, **stretch** or **long_shot**.",
        "",
        "| Tier | Meaning |",
        "| --- | --- |",
        "| strong | Meets every requirement and most nice-to-haves |",
        "| good | Meets every requirement, at most one only partly, a few gaps |",
        "| stretch | Misses one requirement, or only partly meets two or more |",
        "| long_shot | Misses two or more requirements, or the major or graduation date doesn't fit |",
        "",
        "Ignore location: it never affects the score. Citizenship and clearance never affect it either.",
        "",
        "## The student (made up)",
        "",
        f"- {edu.major} at {edu.school}, graduating {edu.grad_date}, {profile.class_standing}",
        f"- Skills: {skills}",
        *[f"- {x.title}, {x.org}: {'; '.join(x.highlights)}" for x in profile.experience],
        *[f"- Project: {p.name}: {p.summary}" for p in profile.projects],
        f"- Coursework: {', '.join(profile.coursework)}",
        "",
    ]
    for i, p in enumerate(postings, 1):
        lines += [
            f"## {i}. {p['company']}: {p['title']}",
            "",
            "**Your tier:** ",
            "",
            f"Full posting: {p['url']}",
            "",
            "<details><summary>Description</summary>",
            "",
            p["description"][:3000] + ("..." if len(p["description"]) > 3000 else ""),
            "",
            "</details>",
            "",
        ]
    (EVAL / "label_sheet.md").write_text("\n".join(lines))
    print(f"wrote {len(postings)} postings")


if __name__ == "__main__":
    main()
