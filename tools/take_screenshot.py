import os
from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def take_screenshot(page: Page, name: str = "debug"):
    os.makedirs("screenshots", exist_ok=True)
    path = f"screenshots/{name}.png"
    logger.info(f"Tool: Capturing screenshot to {path}")
    try:
        await page.screenshot(path=path)
        logger.debug("Screenshot captured successfully.")
        return path
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return None
