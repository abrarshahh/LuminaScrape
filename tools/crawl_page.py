from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

async def crawl_page(page: Page) -> dict:
    """
    Extracts high-quality Markdown and structural data from the current page.
    """
    logger.info("Crawling page content...")
    try:
        # Get raw HTML
        html = await page.content()
        logger.debug(f"Captured HTML content (length: {len(html)})")

        # Basic markdown conversion (simulated or via library)
        # For now, we'll return the innerText as a simple markdown representation
        markdown = await page.evaluate("document.body.innerText")
        logger.info(f"Markdown extraction complete (length: {len(markdown)})")
        
        return {
            "url": page.url,
            "markdown": markdown,
            "html": html
        }
    except Exception as e:
        logger.error(f"Error during page crawl: {e}")
        return {"error": str(e)}
