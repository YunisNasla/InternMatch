import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.llm import PROMPTS_DIR
from app.main import app, get_llm
from tests.test_llm_and_taggers import FakeClaude

RESUME = Path(__file__).parent / "fixtures/resumes/me_diego_ramirez.pdf"
PARSED = json.loads((PROMPTS_DIR / "parser_examples.json").read_text())[1]["assistant"]  # the Long Beach ME student
REFINED = json.dumps({"intent": "update_filters", "reply": "Set up aerospace companies near LA.", "changes": [
    {"field": "industries", "action": "set", "value": ["aerospace_defense"]},
    {"field": "home_city", "action": "set", "value": "Los Angeles, CA"},
    {"field": "emphasis", "action": "set", "value": "rockets"},  # chat-only: dropped in initial mode
]})


@pytest.fixture
def client():
    fake = FakeClaude(lambda system, user, n: REFINED if "<mode>initial" in user else PARSED)
    app.dependency_overrides[get_llm] = lambda: fake
    yield TestClient(app), fake
    app.dependency_overrides.clear()


def test_parse_with_free_text_prefills_filters(client):
    http, fake = client
    body = http.post("/api/parse", files={"file": (RESUME.name, RESUME.read_bytes())},
                     data={"text": "aerospace near LA"}).json()
    assert body["is_stem"] is True
    assert body["filters"]["role_types"] == ["mechanical", "aerospace", "controls_gnc"]
    assert body["filters"]["industries"] == ["aerospace_defense"]
    assert body["filters"]["home_city"] == "Los Angeles, CA"
    assert body["filters"]["emphasis"] is None
    assert len(fake.calls) == 2


def test_parse_without_free_text_skips_prompt_4(client):
    http, fake = client
    body = http.post("/api/parse", files={"file": (RESUME.name, RESUME.read_bytes())}).json()
    assert body["reply"] == "" and body["filters"]["home_city"] == "Long Beach, CA" and len(fake.calls) == 1


def test_parse_rejects_a_text_file_with_a_plain_message(client):
    http, fake = client
    response = http.post("/api/parse", files={"file": ("resume.txt", b"hello")})
    assert response.status_code == 400 and "PDF or Word" in response.json()["detail"] and fake.calls == []


def seed_postings():
    from contextlib import closing

    from app import db
    with closing(db.connect()) as conn:
        for pid, desc in (("greenhouse:acme:1", "Write C firmware for avionics."), ("simplify:2", None)):
            conn.execute(
                "INSERT INTO postings (id, source, company, title, locations, terms, url, posted_at, date_kind, "
                "description, has_description, role_type, work_arrangement, active, sources, first_seen, last_seen) "
                "VALUES (?, 'x', 'Acme', 'Firmware Intern', ?, ?, 'https://x', '2026-10-01T00:00:00Z', 'posted', ?, ?, "
                "'embedded_firmware', 'in_person', 1, '[]', 'x', 'x')",
                (pid, json.dumps(["Hawthorne, CA"]), json.dumps(["Summer 2027"]), desc, int(bool(desc))),
            )
        conn.execute("INSERT INTO companies (name, industry) VALUES ('Acme', 'space')")
        conn.commit()


def test_search_scores_described_postings_and_lists_title_only_ones(client):
    http, fake = client
    from tests.test_scorer import GOOD
    fake.answer = lambda system, user, n: json.dumps(GOOD)
    seed_postings()
    profile = json.loads(PARSED)
    body = http.post("/api/search", json={"profile": profile, "filters": {}}).json()
    assert [c["id"] for c in body["cards"]] == ["greenhouse:acme:1"] and body["cards"][0]["score"]["tier"] == "strong"
    assert [a["id"] for a in body["also_open"]] == ["simplify:2"]
    assert len(fake.calls) == 1 and "simplify:2" not in json.dumps(fake.calls)
    assert '"location"' not in fake.calls[0]["messages"][-1]["content"]  # the field, not a school name
    again = http.post("/api/search", json={"profile": profile, "filters": {}}).json()
    assert again["cards"] == body["cards"] and len(fake.calls) == 1  # served from the cache


def test_search_rejects_a_bad_profile(client):
    http, _ = client
    assert http.post("/api/search", json={"profile": {"is_stem": "maybe"}, "filters": {}}).status_code == 422
