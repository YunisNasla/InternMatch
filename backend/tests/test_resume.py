import io
import json
import zipfile
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
        ("sheet.docx", None, "couldn't open"),  # a zip that isn't a Word file: no library internals in the message
        ("bomb.docx", None, "too large"),  # a real Word file plus a part that is huge when unpacked
        ("xmlbomb.docx", None, "too large"),  # small upload, but its XML would cost gigabytes to parse
    ],
)
def test_rejects_bad_uploads_with_a_plain_message(name, data, message):
    if data is None:
        data = _docx_variant(bomb=name.endswith("bomb.docx"), xml=name == "xmlbomb.docx")
    with pytest.raises(ValueError, match=message) as error:
        extract_text(name, data)
    assert "object at 0x" not in str(error.value)


def _docx_variant(bomb: bool, xml: bool = False) -> bytes:
    """The real fixture with a huge part added (80 MB of media, or 6 MB of XML), or relabeled as a spreadsheet."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(RESUMES / "chem_sam_okafor.docx") as src, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
        for item in src.infolist():
            data = src.read(item)
            if not bomb and item.filename == "[Content_Types].xml":
                data = data.replace(b"wordprocessingml.document.main+xml", b"spreadsheetml.sheet.main+xml")
            out.writestr(item, data)
        if bomb and xml:
            out.writestr("word/padding.xml", b"<w:p/>" * 1_000_000)
        elif bomb:
            out.writestr("word/media/padding.bin", b"0" * 80_000_000)
    return buffer.getvalue()


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
