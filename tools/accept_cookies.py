from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def accept_cookies(page: Page):
    """
    Attempts to find and click 'Accept' buttons on cookie consent banners.
    """
    logger.info("Scanning for cookie consent banners...")
    accept_keywords = [
        "accept", "agree", "allow", "consent", "ok", "got it", "i understand", "accept all", "allow all"
    ]
    reject_keywords = [
        "reject", "decline", "deny", "disagree", "do not", "don't", "manage", "settings", "preferences"
    ]
    
    try:
        # Prefer role=button elements first; then fallback to links.
        candidates = await page.query_selector_all("button, [role='button'], a")
        for el in candidates:
            try:
                if not await el.is_visible():
                    continue
            except Exception:
                continue

            try:
                text = ((await el.inner_text()) or "").strip().lower()
            except Exception:
                text = ""

            if not text:
                continue

            # Avoid clicking reject/manage/settings by accident
            if any(kw in text for kw in reject_keywords):
                continue

            if any(kw in text for kw in accept_keywords):
                logger.info(f"Found potential cookie accept element: '{text}'. Clicking...")
                try:
                    await el.click(timeout=5000)
                except Exception:
                    try:
                        await page.evaluate("(node) => node.click()", el)
                    except Exception:
                        continue
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                logger.info("Cookie banner likely dismissed.")
                return True
        
        logger.debug("No cookie banner buttons found.")
        return False
    except Exception as e:
        logger.error(f"Error handling cookie banner: {e}")
        return False
