from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def clean_dom(page: Page):
    """
    Removes non-essential elements from the DOM to reduce noise and LLM token usage.
    """
    logger.info("Starting DOM cleanup to reduce noise...")
    try:
        # Elements to remove
        selectors = [
            "script", "style", "iframe", "noscript", "svg", "path", 
            "footer", "nav", "header", ".ads", ".sidebar", "#sidebar"
        ]
        
        for selector in selectors:
            logger.debug(f"Removing elements matching: {selector}")
            await page.evaluate(f'document.querySelectorAll("{selector}").forEach(el => el.remove())')
        
        logger.info("DOM cleanup completed successfully.")
    except Exception as e:
        logger.error(f"Error during DOM cleanup: {e}")
