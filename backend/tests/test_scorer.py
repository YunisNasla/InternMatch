import json
import shutil

import pytest

from app import db, llm
from app.matching import cache, scorer
from app.schemas import Profile, ScoreResult
from tests.fakes import FakeClaude

PROFILE = Profile(is_stem=True, class_standing="junior", location={"city": "Zzyzx", "state": "CA"},
                  skills={"programming_languages": ["C"]})
ROW = {"id": "greenhouse:acme:1", "company": "Acme", "title": "Firmware Intern", "industry": "space",
       "role_type": "embedded_firmware", "terms": ["Summer 2027"], "description": "Write C firmware.",
       "has_description": 1}
GOOD = {"requirements": [{"requirement": "C", "type": "must", "evidence": "C", "status": "met"}], "eligibility": [],
        "fit_score": 88, "tier": "good", "confidence": "high", "top_matches": ["C", "a", "b", "c"], "key_gaps": [],
        "recruiter_note": "Strong fit.", "resume_tip": "Lead with firmware."}


def test_profile_hash_ignores_location_only():
    moved = PROFILE.model_copy(update={"location": {"city": "Boston", "state": "MA"}})
    assert cache.profile_hash(moved) == cache.profile_hash(PROFILE)
    assert cache.profile_hash(PROFILE.model_copy(update={"coursework": ["Circuits"]})) != cache.profile_hash(PROFILE)


def test_prompt_version_changes_with_prompt_text(tmp_path, monkeypatch):
    before = cache.prompt_version()
    shutil.copytree(llm.PROMPTS_DIR, tmp_path / "prompts")
    (tmp_path / "prompts/scorer_system.txt").write_text("edited")
    monkeypatch.setattr(llm, "PROMPTS_DIR", tmp_path / "prompts")
    assert cache.prompt_version() != before


def test_tier_follows_score_and_lists_are_capped():
    result = ScoreResult(**GOOD)
    assert result.tier == "strong" and len(result.top_matches) == 3
    assert ScoreResult(**GOOD | {"fit_score": 49}).tier == "long_shot"


def test_cache_key_includes_emphasis_and_version(tmp_path):
    conn = db.connect()
    cache.put(conn, "h", "job", None, "v1", ScoreResult(**GOOD))
    assert cache.get(conn, "h", "job", None, "v1") is not None
    assert cache.get(conn, "h", "job", "controls work", "v1") is None
    assert cache.get(conn, "h", "job", None, "v2") is None
    assert cache.fallback(conn, "h", "job").fit_score == 88


async def test_scorer_never_sends_location_and_uses_the_cache(tmp_path):
    conn = db.connect()
    fake = FakeClaude(lambda system, user, n: json.dumps(GOOD))
    results, unscored = await scorer.score(fake, conn, PROFILE, [ROW], None)
    assert results[ROW["id"]].fit_score == 88 and unscored == []
    call = fake.calls[0]
    assert "Zzyzx" not in json.dumps(call) and "embedded firmware roles at space companies" in call["system"]
    assert "{emphasis_block}" not in call["system"] and "extra weight" not in call["system"]
    assert call["output_config"] == {"effort": "low"}
    await scorer.score(fake, conn, PROFILE, [ROW], None)
    assert len(fake.calls) == 1  # second search comes from the cache


async def test_emphasis_reaches_the_prompt_and_rescores(tmp_path):
    conn = db.connect()
    fake = FakeClaude(lambda system, user, n: json.dumps(GOOD))
    await scorer.score(fake, conn, PROFILE, [ROW], None)
    await scorer.score(fake, conn, PROFILE, [ROW], "hands-on controls work")
    assert len(fake.calls) == 2
    assert "The candidate asked you to give extra weight to: hands-on controls work." in fake.calls[1]["system"]


async def test_failed_call_falls_back_to_any_cached_score_else_unscored(tmp_path):
    conn = db.connect()
    await scorer.score(FakeClaude(lambda *a: json.dumps(GOOD)), conn, PROFILE, [ROW], None)
    broken = FakeClaude(lambda *a: "not json")
    results, unscored = await scorer.score(broken, conn, PROFILE, [ROW], "new emphasis")
    assert results[ROW["id"]].fit_score == 88 and unscored == []
    other = ROW | {"id": "greenhouse:acme:2"}
    results, unscored = await scorer.score(broken, conn, PROFILE, [other], None)
    assert results == {} and unscored == [other["id"]]


async def test_title_only_postings_are_refused():
    with pytest.raises(ValueError):
        await scorer.score(FakeClaude(lambda *a: "{}"), None, PROFILE, [ROW | {"has_description": 0}], None)
