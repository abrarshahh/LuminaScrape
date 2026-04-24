from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def scroll_page(page: Page, distance: int = 500):
    logger.info(f"Tool: Scrolling page by {distance} pixels")
    try:
        await page.evaluate(f"window.scrollBy(0, {distance})")
        logger.debug("Scroll completed.")
    except Exception as e:
        logger.error(f"Failed to scroll page: {e}")
