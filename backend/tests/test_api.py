import json
from pathlib import Path

import pytest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.llm import PROMPTS_DIR
from app.main import app, get_llm
from tests.fakes import FakeClaude

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


def test_refine_applies_emphasis_and_the_next_search_rescores(client):
    http, fake = client
    from tests.test_scorer import GOOD
    seed_postings()
    profile = json.loads(PARSED)
    fake.answer = lambda system, user, n: json.dumps(GOOD)
    http.post("/api/search", json={"profile": profile, "filters": {}})
    fake.answer = lambda system, user, n: json.dumps({"intent": "update_filters", "reply": "Weighing controls work.",
        "changes": [{"field": "emphasis", "action": "set", "value": "controls work"}]})
    body = http.post("/api/refine", json={"filters": {}, "message": "I care more about controls work"}).json()
    assert body["filters"]["emphasis"] == "controls work" and body["reply"] == "Weighing controls work."
    assert "<mode>refine</mode>" in fake.calls[-1]["messages"][-1]["content"]
    fake.answer = lambda system, user, n: json.dumps(GOOD)
    calls = len(fake.calls)
    http.post("/api/search", json={"profile": profile, "filters": body["filters"]})
    assert len(fake.calls) == calls + 1 and "controls work" in fake.calls[-1]["system"]


def test_refine_rejects_an_empty_message(client):
    http, _ = client
    assert http.post("/api/refine", json={"filters": {}, "message": ""}).status_code == 422


def test_city_check(client):
    http, _ = client
    assert http.get("/api/city", params={"q": "Pomona, CA"}).json() == {"found": True}
    assert http.get("/api/city", params={"q": "Pamona, CA"}).json() == {"found": False}


def test_search_and_parse_say_whether_the_home_city_was_found(client):
    http, fake = client
    from tests.test_scorer import GOOD
    seed_postings()
    fake.answer = lambda system, user, n: json.dumps(GOOD)
    profile = json.loads(PARSED)
    found = http.post("/api/search", json={"profile": profile, "filters": {"home_city": "Pomona, CA"}}).json()
    missing = http.post("/api/search", json={"profile": profile, "filters": {"home_city": "Pamona, CA"}}).json()
    assert found["home_city_found"] is True and missing["home_city_found"] is False


def test_oversized_upload_is_refused_before_it_is_read(client):
    http, fake = client
    body = b"x" * (6 * 1024 * 1024)
    response = http.post("/api/parse", content=body, headers={"content-type": "multipart/form-data; boundary=b"})
    assert response.status_code == 413 and fake.calls == []
    # CORS must wrap the guard, or the browser hides the 413 message behind a network error.
    assert app.user_middleware[0].cls is CORSMiddleware


def test_search_rejects_an_oversized_profile(client):
    http, _ = client
    profile = json.loads(PARSED) | {"coursework": ["x" * 30_000]}
    assert http.post("/api/search", json={"profile": profile, "filters": {}}).status_code == 422


def test_also_open_is_capped_with_a_total(client):
    http, fake = client
    from contextlib import closing

    from app import db
    with closing(db.connect()) as conn:
        for i in range(60):
            conn.execute(
                "INSERT INTO postings (id, source, company, title, locations, terms, url, posted_at, date_kind, "
                "description, has_description, role_type, work_arrangement, active, sources, first_seen, last_seen) "
                "VALUES (?, 'simplify', 'Acme', 'Intern', '[]', ?, 'https://x', NULL, 'unknown', NULL, 0, 'software', "
                "'not_stated', 1, '[]', 'x', 'x')",
                (f"simplify:{i}", json.dumps(["Summer 2027"])),
            )
        conn.commit()
    body = http.post("/api/search", json={"profile": json.loads(PARSED), "filters": {}}).json()
    assert len(body["also_open"]) == 50 and body["also_open_total"] == 60 and fake.calls == []


def test_posts_from_other_sites_are_refused_before_any_work(client, monkeypatch):
    http, fake = client
    monkeypatch.setattr("app.main.settings.cors_origins", "http://localhost:5173")
    upload = {"files": {"file": (RESUME.name, RESUME.read_bytes())}}
    evil = http.post("/api/parse", headers={"origin": "https://evil.example"}, **upload)
    assert evil.status_code == 403 and fake.calls == []
    assert http.post("/api/search", headers={"origin": "https://evil.example"}, json={}).status_code == 403
    assert http.post("/api/parse", headers={"origin": "http://localhost:5173"}, **upload).status_code == 200
    assert http.post("/api/parse", **upload).status_code == 200  # no Origin: a script or curl on this machine


def test_only_posts_to_parse_get_the_size_check(client):
    http, _ = client
    assert http.delete("/api/parse").status_code == 405
