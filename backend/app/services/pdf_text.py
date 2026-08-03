import re
from io import BytesIO

from pypdf import PdfReader

from app.config import settings


def extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        parts.append(t)
    raw = "\n".join(parts)
    raw = re.sub(r"\s+", " ", raw).strip()
    if len(raw) > settings.max_pdf_text_chars:
        raw = raw[: settings.max_pdf_text_chars]
    return raw


def jaccard_word_similarity(a: str, b: str) -> float:
    if not a.strip() and not b.strip():
        return 1.0
    sa = set(re.findall(r"\w+", a.lower()))
    sb = set(re.findall(r"\w+", b.lower()))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0
