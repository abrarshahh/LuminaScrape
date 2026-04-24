import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

class ContentCrawler:
    def __init__(self):
        # We'll use the async context manager for each crawl to ensure clean sessions
        self.browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True
        )
        self.run_config = CrawlerRunConfig(
            cache_mode="bypass"
        )

    async def crawl(self, url: str) -> str:
        """
        Extracts clean markdown from a URL using AsyncWebCrawler.
        """
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=self.run_config
                )
                return result.markdown
        except Exception as e:
            print(f"Error crawling {url}: {e}")
            return None

    async def crawl_batch(self, urls: list[str]) -> list[str]:
        """
        Extracts markdown from multiple URLs in a batch.
        """
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                results = await crawler.arun_many(
                    urls=urls,
                    config=self.run_config
                )
                return [res.markdown for res in results]
        except Exception as e:
            print(f"Error in batch crawl: {e}")
            return []
