from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def click_element(page: Page, selector: str):
    logger.info(f"Tool: Clicking element '{selector}'")
    try:
        await page.click(selector, timeout=10000)
        logger.debug(f"Successfully clicked '{selector}'")
    except Exception as e:
        logger.error(f"Failed to click '{selector}': {e}")
