from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from playwright.async_api import Page

from core.logger import get_logger

logger = get_logger(__name__)


def classify_resource_url(url: str) -> str:
    url_lc = (url or "").lower()
    if url_lc.startswith("mailto:"):
        return "email"
    if url_lc.startswith("tel:"):
        return "phone"
    if url_lc.endswith(".pdf"):
        return "pdf"
    if url_lc.endswith((".doc", ".docx")):
        return "word"
    if url_lc.endswith((".xls", ".xlsx")):
        return "excel"
    if url_lc.endswith((".ppt", ".pptx")):
        return "powerpoint"
    if url_lc.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp")):
        return "image"
    if url_lc.endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")):
        return "video"
    if url_lc.endswith((".zip", ".rar", ".7z", ".tar", ".gz")):
        return "archive"
    return "html"


async def extract_page_resources(
    page: Page,
    *,
    include_anchors: bool = True,
    include_images: bool = True,
    include_embeds: bool = True,
    max_items: int = 2000,
) -> List[Dict[str, Any]]:
    """
    Extracts page resources from the currently loaded Playwright page.

    Returns a list of dicts:
      { "text": Optional[str], "url": str, "type": str }
    """
    base_url = page.url
    results: List[Dict[str, Any]] = []

    def _add(text: Optional[str], url: str, typ: str) -> None:
        if not url:
            return
        results.append({"text": text.strip() if isinstance(text, str) else None, "url": url, "type": typ})

    try:
        if include_anchors:
            anchors = await page.query_selector_all("a[href]")
            for a in anchors:
                href = await a.get_attribute("href")
                if not href:
                    continue
                abs_url = urljoin(base_url, href)
                text = (await a.inner_text()) if a else None
                _add(text, abs_url, classify_resource_url(abs_url))
                if len(results) >= max_items:
                    return results

        if include_images:
            imgs = await page.query_selector_all("img[src]")
            for img in imgs:
                src = await img.get_attribute("src")
                if not src:
                    continue
                abs_url = urljoin(base_url, src)
                alt = await img.get_attribute("alt")
                _add(alt, abs_url, "image")
                if len(results) >= max_items:
                    return results

        if include_embeds:
            selectors = ["iframe[src]", "embed[src]", "object[data]"]
            for sel in selectors:
                els = await page.query_selector_all(sel)
                for el in els:
                    src = await (el.get_attribute("src") or el.get_attribute("data"))
                    if not src:
                        continue
                    abs_url = urljoin(base_url, src)
                    _add(None, abs_url, classify_resource_url(abs_url))
                    if len(results) >= max_items:
                        return results

        return results
    except Exception as e:
        logger.error(f"Failed to extract page resources: {e}")
        return results

