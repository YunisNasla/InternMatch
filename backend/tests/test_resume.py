import io
import json
import struct
import subprocess
import sys
import zipfile
import zlib
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
        ("renamed_xmlbomb.docx", None, "too large"),  # the same, with the document part renamed so its name hides it
        ("bzip2.docx", None, "couldn't open"),  # Word only writes deflate; bzip2 can pack gigabytes into a few bytes
    ],
)
def test_rejects_bad_uploads_with_a_plain_message(name, data, message):
    if data is None:
        data = _docx_variant(bomb=name.endswith("bomb.docx"), xml="xmlbomb" in name, renamed=name.startswith("renamed"),
                             bzip2=name == "bzip2.docx", sheet=name == "sheet.docx")
    with pytest.raises(ValueError, match=message) as error:
        extract_text(name, data)
    assert "object at 0x" not in str(error.value)


def _docx_variant(bomb: bool, xml: bool = False, renamed: bool = False, bzip2: bool = False, sheet: bool = False) -> bytes:
    """The real fixture with a huge part added (80 MB of media, or 6 MB of XML), or relabeled as a spreadsheet."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(RESUMES / "chem_sam_okafor.docx") as src, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
        for item in src.infolist():
            data = src.read(item)
            if sheet and item.filename == "[Content_Types].xml":
                data = data.replace(b"wordprocessingml.document.main+xml", b"spreadsheetml.sheet.main+xml")
            if renamed:  # Word finds parts by the names in [Content_Types].xml and the .rels files, not by extension
                data = data.replace(b"document.xml", b"document.dat")
                item.filename = item.filename.replace("document.xml", "document.dat")
            if bzip2 and item.filename == "docProps/app.xml":  # a real, valid part, just compressed with bzip2
                item.compress_type = zipfile.ZIP_BZIP2
            out.writestr(item, data)
        if bomb and xml:
            out.writestr("word/padding.dat" if renamed else "word/padding.xml", b"<w:p/>" * 1_000_000)
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


def _lying_size_docx(claimed: int = 1500, real: int = 1 << 30) -> bytes:
    """The fixture with [Content_Types].xml swapped for `real` bytes of deflated zeros that claim to be `claimed` long,
    with a checksum matching the claim, so the size caps, the image peek and the CRC check all pass."""
    with zipfile.ZipFile(RESUMES / "chem_sam_okafor.docx") as z:
        parts = [(i.filename, z.read(i)) for i in z.infolist()]
    bomb = zlib.compressobj(9, zlib.DEFLATED, -15)
    bomb_data = b"".join(bomb.compress(b"\0" * (1 << 24)) for _ in range(real >> 24)) + bomb.flush()
    body, central = b"", b""
    for name, raw in parts:
        n = name.encode()
        if name == "[Content_Types].xml":
            comp, size, crc = bomb_data, claimed, zlib.crc32(b"\0" * claimed)
        else:
            c = zlib.compressobj(9, zlib.DEFLATED, -15)
            comp, size, crc = c.compress(raw) + c.flush(), len(raw), zlib.crc32(raw)
        central += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0, 8, 0, 0x21, crc, len(comp), size, len(n),
                               0, 0, 0, 0, 0, len(body)) + n
        body += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0, 8, 0, 0x21, crc, len(comp), size, len(n), 0) + n + comp
    return body + central + struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(parts), len(parts), len(central), len(body), 0)


def test_a_part_that_lies_about_its_size_cannot_inflate_far_past_it(tmp_path):
    path = tmp_path / "lying.docx"
    path.write_bytes(_lying_size_docx())
    code = ("import resource, sys\nfrom app.resume.extract import extract_text\n"
            "try:\n    extract_text('x.docx', open(sys.argv[1], 'rb').read())\nexcept ValueError:\n    pass\n"
            "print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)")
    out = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, text=True, check=True,
                         cwd=Path(__file__).parents[1]).stdout
    peak_mb = int(out) / (1 << 20 if sys.platform == "darwin" else 1 << 10)  # ru_maxrss is bytes on macOS, KB on Linux
    assert peak_mb < 300, f"peak {peak_mb:.0f} MB"
