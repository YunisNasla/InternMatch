"""Resume text from an uploaded PDF or Word file, in memory only. The file is never written to disk."""

import io
import zipfile
from pathlib import Path

import docx
import pdfplumber

MAX_BYTES = 5 * 1024 * 1024
# shortcut: resumes are 1 to 2 pages; these caps stop a huge PDF from stalling the server or the parser call. Raise them if real CVs get cut off.
MAX_PAGES = 6
MAX_CHARS = 30_000
# A Word file is a zip. Any part may be parsed as XML (Word finds parts through [Content_Types].xml, not by name), and
# XML costs about 50x its size in memory, so everything except recognised images shares a tight cap.
MAX_UNPACKED = 50 * 1024 * 1024
MAX_NON_IMAGE = 5 * 1024 * 1024
# zipfile inflates up to 2 GB per step before trimming a part to its declared size, so a part that lies about its
# size could cost gigabytes even though the file is refused. 16 MB steps keep the overshoot small; much smaller steps
# make zipfile's buffer growth costly on large honest parts (measured: 1 MB steps took a 45 MB part to 1 GB).
# Process-wide, and only changes the step size of reads.
zipfile.ZipExtFile.MAX_N = 16 << 20
_IMAGE_MAGIC = (b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"BM", b"II*\x00", b"MM\x00*", b"\x01\x00\x00\x00", b"\xd7\xcd\xc6\x9a")


class _TooLarge(Exception):
    pass


def extract_text(filename: str, data: bytes) -> str:
    """Plain text of the resume. Raises ValueError with a message the user can act on."""
    if len(data) > MAX_BYTES:
        raise ValueError("That file is over 5 MB. Upload a smaller PDF or Word file.")
    suffix = Path(filename).suffix.lower()
    is_pdf = suffix == ".pdf" and data.startswith(b"%PDF")
    if not is_pdf and not (suffix == ".docx" and data.startswith(b"PK")):
        raise ValueError("Upload a PDF or Word (.docx) file.")
    try:
        if is_pdf:
            # shortcut: a PDF whose streams unpack to gigabytes can still use a lot of memory; fine while the app runs
            # locally on the student's own file, cap stream sizes before deploying publicly.
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages[:MAX_PAGES])
        else:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                parts = z.infolist()
                # Word only writes stored or deflate parts. Other methods (bzip2, LZMA) unpack in big unchecked
                # chunks, so even peeking at their first bytes could cost gigabytes: refuse before opening any part.
                if any(p.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for p in parts):
                    raise ValueError("not a Word file")
                non_image = sum(p.file_size for p in parts if not z.open(p).read(4).startswith(_IMAGE_MAGIC))
            if non_image > MAX_NON_IMAGE or sum(p.file_size for p in parts) > MAX_UNPACKED:
                raise _TooLarge
            document = docx.Document(io.BytesIO(data))
            cells = (cell.text for table in document.tables for row in table.rows for cell in row.cells)
            text = "\n".join([*(p.text for p in document.paragraphs), *cells])
    except _TooLarge:
        raise ValueError("That file is too large to read. Upload a smaller PDF or Word file.") from None
    except Exception as error:  # broken files make the readers raise all sorts of errors, with internals in them
        raise ValueError("We couldn't open that file. Try saving it again as a PDF.") from error
    if not text.strip():
        raise ValueError("We couldn't find any text in that file. If it's a scanned image, upload a text-based PDF.")
    return text.strip()[:MAX_CHARS]
