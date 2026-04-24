from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def accept_cookies(page: Page):
    """
    Attempts to find and click 'Accept' buttons on cookie consent banners.
    """
    logger.info("Scanning for cookie consent banners...")
    cookie_keywords = [
        "accept", "agree", "allow", "consent", "ok", "got it", "i understand"
    ]
    
    try:
        # Search for buttons with cookie keywords
        buttons = await page.query_selector_all("button, a")
        for button in buttons:
            text = (await button.inner_text()).lower()
            if any(kw in text for kw in cookie_keywords):
                logger.info(f"Found potential cookie button: '{text}'. Clicking...")
                await button.click()
                await page.wait_for_load_state("networkidle")
                logger.info("Cookie banner dismissed.")
                return True
        
        logger.debug("No cookie banner buttons found.")
        return False
    except Exception as e:
        logger.error(f"Error handling cookie banner: {e}")
        return False
