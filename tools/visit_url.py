import asyncio
import random
from urllib.parse import urlparse
from playwright.async_api import Page, BrowserContext

async def apply_stealth(page):
    try:
        import playwright_stealth

        stealth_cls = getattr(playwright_stealth, "Stealth", None)
        if stealth_cls is not None:
            stealth_obj = stealth_cls()
            if hasattr(stealth_obj, "apply_stealth_async"):
                await stealth_obj.apply_stealth_async(page)
                return
            if hasattr(stealth_obj, "apply_stealth"):
                res = stealth_obj.apply_stealth(page)
                if asyncio.iscoroutine(res):
                    await res
                return

        stealth_async = getattr(playwright_stealth, "stealth_async", None)
        if callable(stealth_async):
            await stealth_async(page)
            return

        stealth_fn = getattr(playwright_stealth, "stealth", None)
        if callable(stealth_fn):
            res = stealth_fn(page)
            if asyncio.iscoroutine(res):
                await res
            return

        from playwright_stealth.stealth import Stealth

        stealth_obj = Stealth()
        await stealth_obj.apply_stealth_async(page)
    except Exception:
        pass

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

async def visit_url(page: Page, url: str, wait_until: str = "networkidle", timeout: int = 60000) -> dict:
    """
    Navigates the page to the specified URL using stealth techniques and custom user agents.
    """
    try:
        # Apply stealth and custom UA
        ua = random.choice(USER_AGENTS)
        await page.set_extra_http_headers({"User-Agent": ua})
        
        await apply_stealth(page)
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)

        # Navigate to the URL
        response = await page.goto(url, wait_until=wait_until, timeout=timeout)
        
        if not response:
            return {"status": "failed", "reason": "No response received"}
            
        if response.status >= 400:
            return {"status": "failed", "reason": f"HTTP {response.status}", "url": page.url}

        # Small delay to allow dynamic content to settle
        await asyncio.sleep(2)
        
        return {
            "status": "success",
            "url": page.url,
            "http_status": response.status,
            "user_agent": ua
        }
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
