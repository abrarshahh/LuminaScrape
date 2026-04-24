import httpx
import xml.etree.ElementTree as ET
from core.logger import get_logger

logger = get_logger(__name__)

async def parse_sitemap(url: str):
    logger.info(f"Tool: Parsing sitemap for {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            logger.debug(f"Sitemap fetch status: {response.status_code}")
            
            # Simple XML parsing
            root = ET.fromstring(response.text)
            urls = [elem.text for elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
            
            logger.info(f"Found {len(urls)} URLs in sitemap.")
            return urls
    except Exception as e:
        logger.error(f"Failed to parse sitemap: {e}")
        return []
