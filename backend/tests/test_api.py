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
