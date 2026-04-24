import asyncio
import random
from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

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
            "user_agent": ua
        }
    except Exception as e:
        logger.error(f"Error during navigation to {url}: {e}")
        return {"status": "failed", "reason": str(e)}
