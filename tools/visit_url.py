import asyncio
import random
from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

def _extract_locale_hint(url: str) -> str | None:
    """
    Detect locale-like patterns used for region redirects.
    Examples: /en-gb/... or subdomain en-gb.example.com
    """
    try:
        from urllib.parse import urlsplit
        import re

        seg_re = re.compile(r"^[a-z]{2}-[a-z]{2}$", re.I)
        s = urlsplit(url)
        if s.path:
            first = s.path.strip("/").split("/", 1)[0]
            if first and seg_re.match(first):
                return first.lower()
        host = s.hostname or ""
        sub = host.split(".")[0] if "." in host else host
        if sub and seg_re.match(sub):
            return sub.lower()
    except Exception:
        return None
    return None


async def _check_region_redirect_http(url: str, *, timeout_s: float = 15.0, max_hops: int = 8) -> dict:
    """
    Follow HTTP redirects without rendering the page to detect locale/region changes.
    Best-effort only; returns {region_redirect: bool, hops: int, final_url: str}.
    """
    try:
        import httpx
        current = url
        prev_locale = _extract_locale_hint(current)
        hops = 0
        async with httpx.AsyncClient(follow_redirects=False, timeout=timeout_s, headers={"User-Agent": "curl/8"}) as client:
            for _ in range(max_hops):
                r = await client.get(current)
                if r.status_code in (301, 302, 303, 307, 308):
                    loc = r.headers.get("Location")
                    if not loc:
                        break
                    from urllib.parse import urljoin
                    nxt = urljoin(current, loc)
                    hops += 1
                    nxt_locale = _extract_locale_hint(nxt)
                    if prev_locale != nxt_locale and (prev_locale or nxt_locale):
                        return {"region_redirect": True, "hops": hops, "final_url": nxt}
                    current = nxt
                    prev_locale = nxt_locale
                    continue
                break
        return {"region_redirect": False, "hops": hops, "final_url": current}
    except Exception:
        return {"region_redirect": False, "hops": 0, "final_url": url}


async def apply_stealth(page):
    try:
        import playwright_stealth
        if hasattr(playwright_stealth, 'stealth') and hasattr(playwright_stealth.stealth, 'async_api'):
            await playwright_stealth.stealth.async_api(page)
            return
        if hasattr(playwright_stealth, 'stealth_async'):
            await playwright_stealth.stealth_async(page)
            return
    except:
        pass

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

async def visit_url(page: Page, url: str, wait_until: str = "networkidle", timeout: int = 60000) -> dict:
    """
    Navigates the page to the specified URL using stealth techniques.
    """
    logger.info(f"Visiting URL: {url}")
    try:
        region_redirect_info = await _check_region_redirect_http(url)

        ua = random.choice(USER_AGENTS)
        await page.set_extra_http_headers({"User-Agent": ua})
        logger.debug(f"User-Agent set to: {ua}")
        
        await apply_stealth(page)
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = {runtime: {}};
        """)

        logger.debug(f"Navigating with timeout={timeout}, wait_until={wait_until}")
        response = await page.goto(url, wait_until=wait_until, timeout=timeout)
        
        if not response:
            logger.error(f"Navigation to {url} failed: No response")
            return {"status": "failed", "reason": "No response received"}
            
        logger.info(f"Page loaded. Status: {response.status}")
        
        if response.status >= 400:
            logger.warning(f"HTTP Error detected: {response.status}")
            return {"status": "failed", "reason": f"HTTP {response.status}", "url": page.url}

        await asyncio.sleep(2) # Buffer for dynamic content
        
        return {
            "status": "success",
            "url": page.url,
            "http_status": response.status,
            "user_agent": ua,
            "region_redirect": region_redirect_info.get("region_redirect", False),
            "region_redirect_hops": region_redirect_info.get("hops", 0),
            "region_redirect_final_url": region_redirect_info.get("final_url"),
        }
    except Exception as e:
        logger.error(f"Error during navigation to {url}: {e}")
        return {"status": "failed", "reason": str(e)}
