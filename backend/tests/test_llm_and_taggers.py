import json
from types import SimpleNamespace

import httpx
import pytest

from app import db, llm
from app.schemas import TagResult
from tests.test_pipeline import ACME, SIMPLIFY_ROWS, transport


class FakeClaude:
    """Answers like Claude would, from a function of (system, user). Records every call."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        text = self.answer(kw["system"], kw["messages"][-1]["content"], len(self.calls))
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)], usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )


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
    conn = db.connect(tmp_path / "t.db")
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
