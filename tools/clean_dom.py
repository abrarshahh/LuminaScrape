from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def clean_dom(page: Page, *, remove_iframes: bool = False):
    """
    Removes non-essential elements from the DOM to reduce noise and LLM token usage.
    """
    logger.info("Starting DOM cleanup to reduce noise...")
    try:
        # Elements to remove
        selectors = [
            "script", "style", "noscript", "svg", "path", 
            "footer", "nav", "header", ".ads", ".sidebar", "#sidebar"
        ]

        if remove_iframes:
            selectors.append("iframe")
        
        for selector in selectors:
            logger.debug(f"Removing elements matching: {selector}")
            await page.evaluate(f'document.querySelectorAll("{selector}").forEach(el => el.remove())')
        
        logger.info("DOM cleanup completed successfully.")
    except Exception as e:
        logger.error(f"Error during DOM cleanup: {e}")
