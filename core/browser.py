import sys
import asyncio

# Safety check for Windows asyncio loop
def ensure_proactor_loop():
    if sys.platform == "win32":
        try:
            # Check if current loop is already Proactor
            loop = asyncio.get_event_loop()
            if not isinstance(loop, asyncio.ProactorEventLoop):
                # This is tricky mid-execution, but we can at least set the policy
                # for any future loops or subprocess calls
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.async_api import async_playwright

# FINAL ROBUST STEALTH LOADER
async def apply_stealth(page):
    try:
        import playwright_stealth
        if hasattr(playwright_stealth, 'stealth') and hasattr(playwright_stealth.stealth, 'async_api'):
            await playwright_stealth.stealth.async_api(page)
            return
        if hasattr(playwright_stealth, 'stealth_async'):
            await playwright_stealth.stealth_async(page)
            return
        if hasattr(playwright_stealth, 'stealth') and callable(playwright_stealth.stealth):
            res = playwright_stealth.stealth(page)
            if asyncio.iscoroutine(res):
                await res
            return
    except:
        pass

class BrowserManager:
    def __init__(self, headless=True, proxy=None):
        self.headless = headless
        self.proxy = proxy
        self.browser = None
        self.context = None
        self.page = None
        self.pw = None

    async def start(self):
        # Ensure we are using the Proactor loop on Windows before starting Playwright
        ensure_proactor_loop()
        
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        
        await apply_stealth(self.page)
        return self.page

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()

    async def navigate(self, url):
        await self.page.goto(url, wait_until="networkidle")
        return await self.page.content()

    async def screenshot(self, path="screenshot.png"):
        await self.page.screenshot(path=path, full_page=False)
        return path

    async def get_accessibility_tree(self):
        # Simplified accessibility tree capture
        return await self.page.accessibility.snapshot()
