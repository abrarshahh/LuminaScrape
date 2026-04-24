from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def get_accessibility_tree(page: Page) -> dict:
    """
    Captures the accessibility tree for visual/structural analysis.
    """
    logger.debug("Tool: Capturing accessibility tree snapshot")
    try:
        tree = await page.accessibility.snapshot()
        logger.debug("AXTree snapshot captured.")
        return {"accessibility_tree": tree}
    except Exception as e:
        logger.error(f"Failed to capture accessibility tree: {e}")
        return {"error": str(e)}
