import httpx
from core.logger import get_logger

logger = get_logger(__name__)

async def get_robots_txt(url: str):
    logger.info(f"Tool: Fetching robots.txt for {url}")
    try:
        from urllib.parse import urljoin
        robots_url = urljoin(url, "/robots.txt")
        async with httpx.AsyncClient() as client:
            response = await client.get(robots_url)
            logger.debug(f"robots.txt status: {response.status_code}")
            return response.text
    except Exception as e:
        logger.error(f"Failed to fetch robots.txt: {e}")
        return None
