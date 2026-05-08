from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def get_accessibility_tree(page: Page) -> dict:
    """
    Captures the accessibility tree for visual/structural analysis.
    """
    logger.debug("Tool: Capturing accessibility tree snapshot")
    try:
        # In current Playwright Python versions, accessibility is available from the BrowserContext.
        # Keep a page-level fallback for compatibility with older builds.
        tree = None
        try:
            if getattr(page, "context", None) and getattr(page.context, "accessibility", None):
                tree = await page.context.accessibility.snapshot(root=page.main_frame)
            elif getattr(page, "accessibility", None):
                tree = await page.accessibility.snapshot()  # type: ignore[attr-defined]
        except Exception:
            tree = None

        if tree is None:
            return {"accessibility_tree": None, "warning": "Accessibility snapshot unavailable on this runtime"}

        logger.debug("AXTree snapshot captured.")
        return {"accessibility_tree": tree}
    except Exception as e:
        logger.error(f"Failed to capture accessibility tree: {e}")
        return {"error": str(e)}
