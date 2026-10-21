import json

import httpx
import pytest

from app import db, llm
from app.config import settings
from app.schemas import TagResult
from tests.fakes import FakeClaude
from tests.test_pipeline import ACME, SIMPLIFY_ROWS, transport


def test_load_prompt_fills_taxonomy_once_and_leaves_other_braces():
    text = llm.load_prompt("tag_posting_user.txt", company="Acme", title="Intern", locations="LA",
                           description_text="Use {company} templates and {terms}.")
    assert text == '<posting company="Acme" title="Intern" location="LA">Use {company} templates and {terms}.</posting>\n'
    assert "non_stem" in llm.load_prompt("tag_posting_system.txt")
    assert '"Summer 2027"' in llm.TAXONOMY_VARS["supported_terms"]


async def test_call_json_retries_once_with_the_error():
    fake = FakeClaude(lambda system, user, n: "not json" if n == 1 else '{"role_type": "software", "work_arrangement": "remote"}')
    result = await llm.call_json(fake, llm.HAIKU, "sys", "user", TagResult, label="t")
    assert result == TagResult(role_type="software", work_arrangement="remote")
    assert fake.calls[1]["messages"][-1]["content"].startswith("Your last output failed:")


async def test_call_json_gives_up_after_two_bad_outputs():
    fake = FakeClaude(lambda system, user, n: '{"role_type": "astrology", "work_arrangement": "remote"}')
    with pytest.raises(llm.LLMError):
        await llm.call_json(fake, llm.HAIKU, "sys", "user", TagResult, label="t")
    assert len(fake.calls) == 2


def tagger_answers(system, user, n):
    if "assign a company to one industry" in system:
        return '{"industry": "space", "confidence": "high"}'
    role = "non_stem" if "Marketing" in user else "software"
    return json.dumps({"role_type": role, "work_arrangement": "not_stated"})


async def test_pipeline_tags_once_drops_non_stem_and_skips_seed_companies(tmp_path):
    conn = db.connect()
    SIMPLIFY_ROWS.append({"id": "s5", "company_name": "Rocket Lab", "title": "Marketing Intern", "active": True,
                          "terms": ["Summer 2027"], "locations": ["Long Beach, CA"], "date_posted": 1786000000,
                          "url": "https://example.com/marketing"})
    try:
        fake = FakeClaude(tagger_answers)
        async with httpx.AsyncClient(transport=transport()) as client:
            from app.ingest import pipeline
            await pipeline.run(conn, client, ACME, fake)
            first_run_calls = len(fake.calls)
            await pipeline.run(conn, client, ACME, fake)
    finally:
        SIMPLIFY_ROWS.pop()

    assert len(fake.calls) == first_run_calls  # nothing is tagged twice, not even the dropped posting
    ids = {r[0] for r in conn.execute("SELECT id FROM postings")}
    assert "simplify:s5" not in ids
    assert conn.execute("SELECT id FROM dropped").fetchall()[0][0] == "simplify:s5"
    assert conn.execute("SELECT COUNT(*) FROM postings WHERE role_type = 'software'").fetchone()[0] == 2
    company_prompts = [c["messages"][0]["content"] for c in fake.calls if "assign a company" in c["system"]]
    assert len(company_prompts) == 1 and "Rocket Lab" in company_prompts[0]  # Acme is a seed company
    assert all(c["output_config"] == {"effort": "low"} and "temperature" not in c for c in fake.calls)


async def test_a_retried_tag_still_sees_the_stored_description(tmp_path):
    """Run 1's tag call fails; run 2 must tag from the description, not the title, and keep Lever's arrangement."""
    import anthropic
    import httpx as _httpx

    from app.ingest import pipeline

    def flaky(system, user, n):
        if "GNC Intern" in user and n <= 3:
            return anthropic.APIConnectionError(request=_httpx.Request("POST", "https://api"))
        return tagger_answers(system, user, n)

    conn = db.connect()
    fake = FakeClaude(flaky)
    async with httpx.AsyncClient(transport=transport()) as client:
        await pipeline.run(conn, client, ACME, fake)
        await pipeline.run(conn, client, ACME, fake)
    posting_calls = [c for c in fake.calls if "label internship postings" in c["system"]]
    retried = [c for c in posting_calls if "GNC Intern" in c["messages"][-1]["content"]][-1]
    assert "Write guidance code." in retried["messages"][-1]["content"]
    row = conn.execute("SELECT role_type, work_arrangement FROM postings WHERE id LIKE 'lever:rocketlab:%'").fetchone()
    assert tuple(row) == ("software", "remote")


def test_client_without_a_key_says_what_to_set(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm.client()
