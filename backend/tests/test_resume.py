import json
from datetime import date
from pathlib import Path

import pytest

from app.llm import PROMPTS_DIR
from app.resume.extract import MAX_BYTES, extract_text
from app.resume.parser import parse_resume
from tests.fakes import FakeClaude
from tests.fixtures.make_resumes import make_pdf

RESUMES = Path(__file__).parent / "fixtures/resumes"


@pytest.mark.parametrize("name, expect", [("cs_maya_chen.pdf", "Maya Chen"), ("chem_sam_okafor.docx", "Sam Okafor")])
def test_extracts_pdf_and_docx(name, expect):
    assert extract_text(name, (RESUMES / name).read_bytes()).startswith(expect)


@pytest.mark.parametrize(
    "name, data, message",
    [
        ("big.pdf", b"%PDF" + b"0" * MAX_BYTES, "over 5 MB"),
        ("resume.txt", b"plain text", "PDF or Word"),
        ("fake.pdf", b"not a pdf at all", "PDF or Word"),
        ("blank.pdf", make_pdf(""), "any text"),
        ("broken.pdf", b"%PDF-1.4 garbage", "couldn't open"),
    ],
)
def test_rejects_bad_uploads_with_a_plain_message(name, data, message):
    with pytest.raises(ValueError, match=message):
        extract_text(name, data)


async def test_parser_sends_three_examples_then_the_resume():
    example = json.loads((PROMPTS_DIR / "parser_examples.json").read_text())[0]["assistant"]
    fake = FakeClaude(lambda system, user, n: example)
    profile = await parse_resume(fake, "Jane Doe resume text")
    call = fake.calls[0]
    assert [m["role"] for m in call["messages"]] == ["user", "assistant"] * 3 + ["user"]
    assert call["messages"][-1]["content"] == "<resume>\nJane Doe resume text\n</resume>\n"
    assert date.today().isoformat() in call["system"] and "earth_environmental_science" in call["system"]
    assert call["model"] == "claude-sonnet-5-5" and "temperature" not in call
    assert profile.location.city == "Riverside"
