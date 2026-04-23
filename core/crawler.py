import asyncio
from crawl4ai import WebCrawler

class ContentCrawler:
    def __init__(self):
        self.crawler = WebCrawler()
        self.crawler.warmup()

    async def crawl(self, url):
        """
        Extracts clean markdown from a URL.
        """
        try:
            result = self.crawler.run(url=url)
            return result.markdown
        except Exception as e:
            print(f"Error crawling {url}: {e}")
            return None

    async def crawl_batch(self, urls):
        """
        Extracts markdown from multiple URLs.
        """
        results = self.crawler.run_many(urls=urls)
        return [res.markdown for res in results]

# Usage:
# crawler = ContentCrawler()
# markdown = await crawler.crawl("https://example.com")
