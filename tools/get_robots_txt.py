import httpx
import urllib.robotparser
import random
from typing import Optional, Dict
from urllib.parse import urlparse

BROWSER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

async def get_robots_txt(url: str) -> Dict:
    """
    Fetches and parses the robots.txt for the given URL's domain.
    Determines if crawling is allowed for the specified URL.
    
    Args:
        url: The target URL to check.
        
    Returns:
        Dict: Status, robots.txt content, and whether crawling is allowed.
    """
    try:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_url = f"{base_url}/robots.txt"
        
        user_agent = random.choice(BROWSER_USER_AGENTS)
        headers = {"User-Agent": user_agent}

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(robots_url, headers=headers)
            
            if response.status_code == 404:
                return {"status": "success", "allowed": True, "reason": "No robots.txt found (default allow)"}
            
            if response.status_code != 200:
                return {"status": "failed", "reason": f"HTTP {response.status_code} fetching robots.txt"}

            robots_text = response.text
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(robots_text.splitlines())
            
            is_allowed = rp.can_fetch(user_agent, url)
            
            # Extract sitemaps while we're at it
            sitemaps = []
            for line in robots_text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemaps.append(line.split(":", 1)[1].strip())

            return {
                "status": "success",
                "allowed": is_allowed,
                "robots_text": robots_text,
                "sitemaps": sitemaps,
                "user_agent_checked": user_agent
            }
            
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
