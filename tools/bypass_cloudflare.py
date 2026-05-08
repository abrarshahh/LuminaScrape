from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def bypass_cloudflare(page: Page):
    """
    Attempts to bypass Cloudflare waiting rooms and challenges.
    """
    logger.info("Checking for Cloudflare protection...")
    try:
        async def _is_challenge() -> bool:
            html = await page.content()
            if "Checking your browser before accessing" in html:
                return True
            if "Just a moment" in html and "cf-" in html:
                return True
            if "cf-challenge" in html or "cf-turnstile" in html:
                return True
            return False

        # Fast exit if no signals
        if not await _is_challenge():
            logger.debug("No obvious Cloudflare challenge found.")
            return {"status": "no_challenge"}

        logger.warning("Cloudflare challenge detected. Waiting for resolution...")
        # Wait loop: challenges can take time or require a reload
        for attempt in range(1, 6):
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass

            if not await _is_challenge():
                logger.info("Cloudflare challenge appears cleared.")
                return {"status": "cleared", "attempts": attempt}

            # Try a gentle reload after a couple attempts
            if attempt in (3, 5):
                logger.warning("Cloudflare still present; reloading page to retry challenge.")
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=60000)
                except Exception:
                    pass

        # If still challenged, capture a screenshot for debugging (best-effort)
        try:
            import os
            os.makedirs("screenshots", exist_ok=True)
            await page.screenshot(path="screenshots/cloudflare_block.png", full_page=False)
        except Exception:
            pass
        logger.warning("Cloudflare challenge not cleared after retries.")
        return {"status": "blocked"}
    except Exception as e:
        logger.error(f"Error during Cloudflare bypass: {e}")
        return {"status": "error", "reason": str(e)}
