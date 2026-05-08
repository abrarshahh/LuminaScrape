from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


class _TextExtractor(HTMLParser):
    """
    Minimal HTML -> text extractor that:
    - drops script/style/noscript
    - keeps block-ish separators to avoid word-smashing
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_stack: List[str] = []
        self._chunks: List[str] = []

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        t = tag.lower()
        if t in {"script", "style", "noscript", "svg", "iframe", "head"}:
            self._skip_stack.append(t)
            return
        if t in {"p", "br", "div", "section", "article", "main", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str):  # type: ignore[override]
        t = tag.lower()
        if self._skip_stack and self._skip_stack[-1] == t:
            self._skip_stack.pop()
            return
        if t in {"p", "div", "section", "article", "main", "li", "tr"}:
            self._chunks.append("\n")

    def handle_data(self, data: str):  # type: ignore[override]
        if self._skip_stack:
            return
        txt = data.strip()
        if not txt:
            return
        self._chunks.append(txt + " ")

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


async def extract_text_from_html(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


async def scrape_static_text(url: str, *, timeout_s: float = 45.0) -> Optional[str]:
    """
    Fetch a URL via HTTP and return cleaned text (no browser).
    Returns None on failure or non-HTML content.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
    except Exception:
        return None

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            resp = await client.get(url, timeout=timeout_s)
            resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").lower()
            if "html" not in ctype and "text/" not in ctype:
                return None
            return await extract_text_from_html(resp.text)
    except Exception as e:
        logger.error(f"Static text scrape failed for {url}: {e}")
        return None

