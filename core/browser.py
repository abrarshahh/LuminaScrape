import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

class BrowserManager:
    def __init__(self, headless=True, proxy=None):
        self.headless = headless
        self.proxy = proxy
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        self.pw = await async_playwright().start()
        browser_args = {}
        if self.proxy:
            browser_args["proxy"] = {"server": self.proxy}
        
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        await stealth_async(self.page)
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
