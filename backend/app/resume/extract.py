"""Resume text from an uploaded PDF or Word file, in memory only. The file is never written to disk."""

import io
from pathlib import Path

import docx
import pdfplumber

MAX_BYTES = 5 * 1024 * 1024
# shortcut: resumes are 1 to 2 pages; these caps stop a huge PDF from stalling the server or the parser call.
MAX_PAGES = 6
MAX_CHARS = 30_000


def extract_text(filename: str, data: bytes) -> str:
    """Plain text of the resume. Raises ValueError with a message the user can act on."""
    if len(data) > MAX_BYTES:
        raise ValueError("That file is over 5 MB. Upload a smaller PDF or Word file.")
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf" and data.startswith(b"%PDF"):
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages[:MAX_PAGES])
        elif suffix == ".docx" and data.startswith(b"PK"):
            document = docx.Document(io.BytesIO(data))
            cells = (cell.text for table in document.tables for row in table.rows for cell in row.cells)
            text = "\n".join([*(p.text for p in document.paragraphs), *cells])
        else:
            raise ValueError("Upload a PDF or Word (.docx) file.")
    except ValueError:
        raise
    except Exception as error:  # a broken file makes the PDF and DOCX readers raise all sorts of errors
        raise ValueError("We couldn't open that file. Try saving it again as a PDF.") from error
    if not text.strip():
        raise ValueError("We couldn't find any text in that file. If it's a scanned image, upload a text-based PDF.")
    return text.strip()[:MAX_CHARS]
