import sqlite3
from pathlib import Path

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS postings (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    locations TEXT NOT NULL,
    terms TEXT NOT NULL,
    url TEXT NOT NULL,
    ats_job_id TEXT,
    posted_at TEXT,
    date_kind TEXT NOT NULL,
    description TEXT,
    has_description INTEGER NOT NULL,
    lever_workplace TEXT,
    role_type TEXT,
    work_arrangement TEXT NOT NULL,
    active INTEGER NOT NULL,
    sources TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS companies (
    name TEXT PRIMARY KEY,
    industry TEXT,
    industry_source TEXT,
    confidence TEXT,
    ats TEXT,
    board TEXT
);
CREATE TABLE IF NOT EXISTS scores (
    profile_hash TEXT NOT NULL,
    job_id TEXT NOT NULL,
    emphasis TEXT NOT NULL,  -- '' when no emphasis, since NULL breaks the primary key
    prompt_version TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (profile_hash, job_id, emphasis, prompt_version)
);
CREATE TABLE IF NOT EXISTS ingest_runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    counts TEXT,
    errors TEXT
);
-- non_stem postings, kept so they are never tagged again
CREATE TABLE IF NOT EXISTS dropped (id TEXT PRIMARY KEY);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or settings.db_file
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def last_ingest(conn: sqlite3.Connection) -> str | None:
    return conn.execute("SELECT MAX(finished_at) FROM ingest_runs").fetchone()[0]
