from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def type_text(page: Page, selector: str, text: str):
    logger.info(f"Tool: Typing text into '{selector}'")
    try:
        await page.fill(selector, text, timeout=10000)
        logger.debug(f"Successfully typed into '{selector}'")
    except Exception as e:
        logger.error(f"Failed to type into '{selector}': {e}")
