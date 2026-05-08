from __future__ import annotations

from typing import Optional

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


async def download_image_bytes(url: str, *, timeout_s: float = 60.0) -> Optional[bytes]:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=timeout_s)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.error(f"Failed downloading image from {url}: {e}")
        return None


def ocr_image_bytes(image_bytes: bytes) -> Optional[str]:
    """
    OCR helper with optional dependencies.

    Priority:
    - pytesseract + Pillow (fast, common)
    - easyocr (heavier)
    """
    try:
        import io
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore

        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        text = (text or "").strip()
        return text or None
    except Exception:
        pass

    try:
        import easyocr  # type: ignore
        import numpy as np  # type: ignore
        import cv2  # type: ignore

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        reader = easyocr.Reader(["en"], gpu=False)
        lines = reader.readtext(img, detail=0)
        text = "\n".join([ln.strip() for ln in lines if ln and ln.strip()]).strip()
        return text or None
    except Exception:
        logger.warning("OCR deps not installed (pytesseract/PIL or easyocr stack).")
        return None


async def ocr_image_url(url: str, *, timeout_s: float = 60.0) -> Optional[str]:
    b = await download_image_bytes(url, timeout_s=timeout_s)
    if not b:
        return None
    return ocr_image_bytes(b)

