from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def bypass_cloudflare(page: Page):
    """
    Attempts to bypass Cloudflare waiting rooms and challenges.
    """
    logger.info("Checking for Cloudflare protection...")
    try:
        # Check for common Cloudflare strings
        content = await page.content()
        if "Checking your browser before accessing" in content or "cf-challenge" in content:
            logger.warning("Cloudflare challenge detected. Waiting for resolution...")
            # Wait for the challenge to pass or for a specific element to disappear
            await page.wait_for_load_state("networkidle", timeout=30000)
            logger.info("Cloudflare challenge cleared.")
        else:
            logger.debug("No obvious Cloudflare challenge found.")
    except Exception as e:
        logger.error(f"Error during Cloudflare bypass: {e}")
