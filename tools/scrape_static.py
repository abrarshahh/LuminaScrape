import httpx
from core.logger import get_logger

logger = get_logger(__name__)

async def scrape_static(url: str):
    """
    Fast static scraping via HTTP request (no browser).
    """
    logger.info(f"Tool: Performing static scrape for {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            logger.debug(f"Static scrape status: {response.status_code}")
            return response.text
    except Exception as e:
        logger.error(f"Static scrape failed for {url}: {e}")
        return None
