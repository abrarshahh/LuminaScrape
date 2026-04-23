from playwright.async_api import Page
from core.crawler import ContentCrawler
from typing import Dict, Optional

async def crawl_page(page: Page, url: Optional[str] = None) -> Dict:
    """
    Uses Crawl4AI to extract clean markdown from the specified URL or the current page URL.
    
    Args:
        page: The Playwright Page object.
        url: Optional target URL. If not provided, uses page.url.
        
    Returns:
        Dict: Status and extracted markdown.
    """
    try:
        target_url = url or page.url
        if not target_url or target_url == "about:blank":
            return {"status": "failed", "reason": "No valid URL to crawl"}

        crawler = ContentCrawler()
        markdown = await crawler.crawl(target_url)
        
        if markdown:
            return {"status": "success", "url": target_url, "markdown": markdown}
        else:
            return {"status": "failed", "reason": "Crawling returned no content"}
            
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
