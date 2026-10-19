"""Hard filters in code (ARCHITECTURE.md "Prefilter and scoring", step 1)."""

import json
import sqlite3
from datetime import datetime, timedelta

from app.matching import distance
from app.schemas import FilterState


def load_active(conn: sqlite3.Connection) -> list[dict]:
    """Every active posting with its company's industry, JSON columns decoded."""
    rows = conn.execute(
        "SELECT p.*, c.industry FROM postings p LEFT JOIN companies c ON c.name = p.company WHERE p.active = 1"
    )
    return [dict(r) | {"locations": json.loads(r["locations"]), "terms": json.loads(r["terms"])} for r in rows]


def hard_filter(rows: list[dict], f: FilterState, now: datetime) -> tuple[list[dict], int]:
    """(postings that pass, count hidden only because their location couldn't be placed)."""
    terms = set(f.terms) | {"unknown"}
    excluded = {c.casefold() for c in f.exclude_companies}
    oldest = now - timedelta(days=f.posted_within_days) if f.posted_within_days else None
    kept, hidden = [], 0
    for r in rows:
        text = f"{r['title']} {r['description'] or ''}".casefold()
        if (
            (f.industries and r["industry"] not in f.industries)
            or (f.role_types and r["role_type"] not in f.role_types)
            or not terms & set(r["terms"])
            or (oldest and (not r["posted_at"] or datetime.fromisoformat(r["posted_at"]) < oldest))
            or (r["work_arrangement"] != "not_stated" and r["work_arrangement"] not in f.work_arrangements)
            or r["company"].casefold() in excluded
            or not all(k.casefold() in text for k in f.include_keywords)
            or any(k.casefold() in text for k in f.exclude_keywords)
        ):
            continue
        # Distance runs last, so the hidden count covers only postings that passed everything else.
        place = distance.check(r["locations"], r["work_arrangement"], f.home_city, f.max_distance_miles)
        if place == "unplaceable":
            hidden += 1
        elif place == "pass":
            kept.append(r)
    return kept, hidden
