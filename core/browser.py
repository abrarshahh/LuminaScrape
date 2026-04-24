import sys
import asyncio
from playwright.async_api import async_playwright
from core.logger import get_logger

logger = get_logger(__name__)

# Safety check for Windows asyncio loop
def ensure_proactor_loop():
    if sys.platform == "win32":
        try:
            loop = asyncio.get_event_loop()
            if not isinstance(loop, asyncio.ProactorEventLoop):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                logger.debug("Forced Windows ProactorEventLoopPolicy in current context.")
        except Exception as e:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            logger.debug(f"Applied Windows ProactorEventLoopPolicy after error: {e}")

# FINAL ROBUST STEALTH LOADER
async def apply_stealth(page):
    try:
        import playwright_stealth
        logger.debug("Attempting to apply playwright-stealth...")
        
        if hasattr(playwright_stealth, 'stealth') and hasattr(playwright_stealth.stealth, 'async_api'):
            await playwright_stealth.stealth.async_api(page)
            logger.debug("Applied stealth via playwright_stealth.stealth.async_api")
            return

        if hasattr(playwright_stealth, 'stealth_async'):
            await playwright_stealth.stealth_async(page)
            logger.debug("Applied stealth via playwright_stealth.stealth_async")
            return

        if hasattr(playwright_stealth, 'stealth') and callable(playwright_stealth.stealth):
            res = playwright_stealth.stealth(page)
            if asyncio.iscoroutine(res):
                await res
            logger.debug("Applied stealth via callable playwright_stealth.stealth")
            return
            
    except Exception as e:
        logger.warning(f"Could not apply stealth automatically: {e}")
        try:
            from playwright_stealth import Stealth
            stealth_obj = Stealth()
            await stealth_obj.apply_stealth(page)
            logger.debug("Applied stealth via Stealth class fallback")
        except Exception as e2:
            logger.error(f"Total failure applying stealth: {e2}")

class BrowserManager:
    def __init__(self, headless=True, proxy=None):
        self.headless = headless
        self.proxy = proxy
        self.browser = None
        self.context = None
        self.page = None
        self.pw = None
        logger.debug(f"Initialized BrowserManager (headless={headless}, proxy={proxy})")

    async def start(self):
        logger.info("Starting Playwright browser engine...")
        ensure_proactor_loop()
        
        self.pw = await async_playwright().start()
        
        browser_args = {"headless": self.headless}
        if self.proxy:
            browser_args["proxy"] = {"server": self.proxy}
            
        self.browser = await self.pw.chromium.launch(**browser_args)
        logger.debug("Chromium browser launched.")
        
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        logger.debug("New browser context and page created.")
        
        await apply_stealth(self.page)
        return self.page

    async def stop(self):
        logger.info("Stopping Playwright browser engine...")
        if self.browser:
            await self.browser.close()
            logger.debug("Browser closed.")
        if self.pw:
            await self.pw.stop()
            logger.debug("Playwright stopped.")

    async def navigate(self, url):
        logger.info(f"Navigating to {url}")
        await self.page.goto(url, wait_until="networkidle")
        return await self.page.content()

    async def screenshot(self, path="screenshot.png"):
        logger.debug(f"Taking screenshot: {path}")
        await self.page.screenshot(path=path, full_page=False)
        return path

    async def get_accessibility_tree(self):
        logger.debug("Capturing accessibility tree snapshot")
        return await self.page.accessibility.snapshot()
