from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


_FILE_EXTS = re.compile(
    r"\.(?:jpg|jpeg|png|gif|bmp|svg|webp|mp4|avi|mov|wmv|pdf|docx?|xlsx?|pptx?|zip|rar|tar|gz|7z|mp3|wav|ogg|flac|exe|dmg|iso|apk|csv|xml|txt)$",
    re.I,
)


def _normalize_url(url: str) -> str:
    """Normalize URL for deduping (strip fragments, keep query)."""
    parts = urlsplit(url)
    parts = parts._replace(fragment="")
    # Strip default ports
    netloc = parts.netloc
    if netloc.endswith(":80") and parts.scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and parts.scheme == "https":
        netloc = netloc[:-4]
    parts = parts._replace(netloc=netloc)
    return urlunsplit(parts)


def _base_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _in_domain(url: str, base_domain: str) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc:
        return True  # relative
    host = parsed.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return host == base_domain or host.endswith("." + base_domain)


def _looks_like_html_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("", "http", "https"):
        return False
    if _FILE_EXTS.search(parsed.path or ""):
        return False
    if url.startswith(("mailto:", "tel:", "javascript:")):
        return False
    return True


class _HrefExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and v:
                self.hrefs.append(v)


async def _fetch_html_static(client: httpx.AsyncClient, url: str, timeout_s: float) -> Optional[str]:
    try:
        resp = await client.get(url, timeout=timeout_s, follow_redirects=True)
        resp.raise_for_status()
        ctype = (resp.headers.get("content-type") or "").lower()
        if "html" not in ctype and "text/" not in ctype:
            return None
        return resp.text
    except Exception as e:
        logger.debug(f"Static fetch failed for {url}: {e}")
        return None


async def _fetch_html_rendered(url: str, timeout_ms: int) -> Optional[str]:
    """
    Best-effort JS rendering fallback using Playwright.
    This is optional; failures return None.
    """
    try:
        from playwright.async_api import async_playwright  # lazy import
    except Exception:
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="load", timeout=timeout_ms)
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)
            html = await page.content()
            await context.close()
            await browser.close()
            return html
    except Exception as e:
        logger.debug(f"Rendered fetch failed for {url}: {e}")
        return None


async def extract_links_from_html(html: str, base_url: str) -> List[str]:
    parser = _HrefExtractor()
    parser.feed(html)
    out: List[str] = []
    for href in parser.hrefs:
        abs_url = urljoin(base_url, href)
        out.append(_normalize_url(abs_url))
    return out


async def crawl_links_bfs(
    start_url: str,
    max_depth: int = 1,
    *,
    max_pages: int = 200,
    timeout_s: float = 30.0,
    render_timeout_ms: int = 60_000,
    polite_delay_s: float = 0.5,
    use_js_render_fallback: bool = True,
) -> Dict[int, Set[str]]:
    """
    Domain-locked BFS crawler (depth-aware).

    - Uses static HTTP fetch first (httpx).
    - If a page yields zero <a href> links AND use_js_render_fallback is True,
      attempts a headless Playwright render to extract links.
    - Returns {depth: {urls...}} including normalized absolute URLs.
    """
    if not start_url.startswith(("http://", "https://")):
        start_url = "https://" + start_url

    base_domain = _base_domain(start_url)
    visited: Set[str] = set()
    by_depth: Dict[int, Set[str]] = {}

    queue: List[Tuple[str, int]] = [(start_url, 0)]

    async with httpx.AsyncClient(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
    ) as client:
        while queue and len(visited) < max_pages:
            url, depth = queue.pop(0)
            url = _normalize_url(url)

            if url in visited:
                continue
            visited.add(url)

            if depth > max_depth:
                continue

            by_depth.setdefault(depth, set()).add(url)

            if depth == max_depth:
                continue

            await asyncio.sleep(polite_delay_s)

            html = await _fetch_html_static(client, url, timeout_s=timeout_s)
            links: List[str] = []
            if html:
                links = await extract_links_from_html(html, base_url=url)

            if (not links) and use_js_render_fallback:
                rendered = await _fetch_html_rendered(url, timeout_ms=render_timeout_ms)
                if rendered:
                    links = await extract_links_from_html(rendered, base_url=url)

            for link in links:
                if not _looks_like_html_url(link):
                    continue
                if not _in_domain(link, base_domain):
                    continue
                if link not in visited:
                    queue.append((link, depth + 1))

    return by_depth

