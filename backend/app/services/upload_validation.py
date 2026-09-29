"""Reject unsupported, archived, and corrupted uploads before storage."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".docx", ".jpg", ".jpeg", ".png", ".webp", ".gif"})
SUPPORTED_KINDS = ("pdf", "docx", "image")

BLOCKED_EXTENSIONS = frozenset(
    {
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".tgz",
        ".bz2",
        ".xz",
        ".exe",
        ".dll",
        ".msi",
        ".bat",
        ".cmd",
        ".ps1",
        ".js",
        ".mjs",
        ".html",
        ".htm",
        ".iso",
        ".apk",
        ".dmg",
        ".pkg",
        ".deb",
        ".rpm",
        ".doc",  # legacy Word — only .docx is supported
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".txt",
        ".csv",
        ".json",
        ".xml",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
    }
)

BLOCKED_MIME_PREFIXES = (
    "application/zip",
    "application/x-zip",
    "application/x-rar",
    "application/x-7z",
    "application/x-tar",
    "application/gzip",
    "application/x-gzip",
    "multipart/x-zip",
)

UNSUPPORTED_MSG = (
    "Unsupported file type. Upload PDF, Word (.docx), or image (JPEG, PNG, WebP, GIF)."
)
ZIP_MSG = "ZIP and other archive files are not supported. Upload PDF, Word (.docx), or an image."
CORRUPT_MSG = {
    "pdf": "Corrupted or unreadable PDF. The file could not be opened and was not accepted.",
    "docx": "Corrupted or unreadable Word (.docx) file. The file could not be opened and was not accepted.",
    "image": "Corrupted or unreadable image. The file could not be opened and was not accepted.",
}


def _ext(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _mime_base(mime: str) -> str:
    return (mime or "").lower().split(";")[0].strip()


def reject_if_blocked(filename: str, mime: str) -> None:
    """Raise ValueError for archives / clearly unsupported types."""
    ext = _ext(filename)
    m = _mime_base(mime)

    if ext == ".zip" or m in (
        "application/zip",
        "application/x-zip-compressed",
        "application/x-zip",
        "multipart/x-zip",
    ):
        raise ValueError(ZIP_MSG)

    if any(m.startswith(p) for p in BLOCKED_MIME_PREFIXES):
        raise ValueError(ZIP_MSG if "zip" in m or "tar" in m or "rar" in m or "7z" in m or "gzip" in m else UNSUPPORTED_MSG)

    if ext in BLOCKED_EXTENSIONS:
        raise ValueError(UNSUPPORTED_MSG)

    if ext and ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(UNSUPPORTED_MSG)


def validate_file_content(kind: str, data: bytes) -> None:
    """Ensure bytes match the declared kind and can be parsed. Raises ValueError."""
    if not data:
        raise ValueError("Empty file.")

    if kind == "pdf":
        if not data.lstrip().startswith(b"%PDF"):
            raise ValueError(CORRUPT_MSG["pdf"])
        try:
            reader = PdfReader(BytesIO(data))
            # Force parse — encrypted empty / truncated PDFs often fail here
            n_pages = len(reader.pages)
        except (PdfReadError, OSError, ValueError) as e:
            raise ValueError(CORRUPT_MSG["pdf"]) from e
        # Header-only / truncated stubs often parse with 0 pages
        if n_pages == 0 and len(data) < 512:
            raise ValueError(CORRUPT_MSG["pdf"])
        return

    if kind == "docx":
        # DOCX is a ZIP; plain .zip without Word parts must not slip through
        if data[:2] != b"PK":
            raise ValueError(CORRUPT_MSG["docx"])
        try:
            from docx import Document

            Document(BytesIO(data))
        except Exception as e:
            raise ValueError(CORRUPT_MSG["docx"]) from e
        return

    if kind == "image":
        try:
            with Image.open(BytesIO(data)) as img:
                img.verify()
            # verify() leaves the image unusable; reopen and load pixels
            with Image.open(BytesIO(data)) as img:
                img.load()
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as e:
            raise ValueError(CORRUPT_MSG["image"]) from e
        return

    raise ValueError(UNSUPPORTED_MSG)
