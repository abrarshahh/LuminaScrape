from __future__ import annotations

from typing import Optional

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


async def download_bytes(url: str, *, timeout_s: float = 60.0) -> Optional[bytes]:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=timeout_s)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.error(f"Failed downloading bytes from {url}: {e}")
        return None


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Optional[str]:
    """
    Extract text from PDF bytes using PyPDF2 if available.
    Returns None if PyPDF2 is not installed or extraction fails.
    """
    try:
        from PyPDF2 import PdfReader  # optional dependency
    except Exception:
        logger.warning("PyPDF2 not installed; PDF text extraction unavailable.")
        return None

    try:
        import io

        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n\n".join(p.strip() for p in parts if p and p.strip())
        return text or None
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return None


async def extract_pdf_text(url: str, *, timeout_s: float = 60.0) -> Optional[str]:
    """
    Download a PDF and extract its text (best-effort).
    """
    b = await download_bytes(url, timeout_s=timeout_s)
    if not b:
        return None
    return extract_text_from_pdf_bytes(b)

