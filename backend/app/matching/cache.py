"""Score cache keyed by (profile hash, job id, emphasis, prompt version). Location is never part of the key."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

from app import llm, taxonomy
from app.schemas import Profile, ScoreResult

SCORER_FILES = ("scorer_system.txt", "scorer_user.txt", "scorer_emphasis.txt")
SCORER_EFFORT = "low"  # part of the version: a different effort gives different scores


def profile_hash(profile: Profile) -> str:
    return hashlib.sha256(json.dumps(profile.model_dump(exclude={"location"}), sort_keys=True).encode()).hexdigest()


def prompt_version() -> str:
    """Changes whenever the scorer prompts, the labels in its persona, the model or the effort change."""
    parts = [(llm.PROMPTS_DIR / f).read_text() for f in SCORER_FILES]
    parts += [json.dumps([taxonomy.ROLE_TYPES, taxonomy.INDUSTRIES]), llm.HAIKU, SCORER_EFFORT]
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()[:12]


def get(conn: sqlite3.Connection, ph: str, job_id: str, emphasis: str | None, version: str) -> ScoreResult | None:
    row = conn.execute(
        "SELECT result_json FROM scores WHERE profile_hash = ? AND job_id = ? AND emphasis = ? AND prompt_version = ?",
        (ph, job_id, emphasis or "", version),
    ).fetchone()
    return ScoreResult.model_validate_json(row[0]) if row else None


def put(conn: sqlite3.Connection, ph: str, job_id: str, emphasis: str | None, version: str, result: ScoreResult) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO scores (profile_hash, job_id, emphasis, prompt_version, result_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ph, job_id, emphasis or "", version, result.model_dump_json(), datetime.now(UTC).isoformat()),
    )
    conn.commit()


def fallback(conn: sqlite3.Connection, ph: str, job_id: str) -> ScoreResult | None:
    """The newest score for this profile and job under any emphasis or prompt version, for when a call fails."""
    row = conn.execute(
        "SELECT result_json FROM scores WHERE profile_hash = ? AND job_id = ? ORDER BY created_at DESC LIMIT 1",
        (ph, job_id),
    ).fetchone()
    return ScoreResult.model_validate_json(row[0]) if row else None
