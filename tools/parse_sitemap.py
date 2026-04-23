import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse

async def parse_sitemap(sitemap_url: str) -> Dict:
    """
    Recursively fetches and parses a sitemap (or sitemap index) to extract all URLs.
    
    Args:
        sitemap_url: The URL of the sitemap file.
        
    Returns:
        Dict: Status and a list of all URLs found.
    """
    found_urls: Set[str] = set()
    sitemaps_to_process: List[str] = [sitemap_url]
    processed_sitemaps: Set[str] = set()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            while sitemaps_to_process:
                current_url = sitemaps_to_process.pop()
                if current_url in processed_sitemaps:
                    continue
                
                response = await client.get(current_url, headers=headers)
                if response.status_code != 200:
                    continue
                
                processed_sitemaps.add(current_url)
                
                try:
                    root = ET.fromstring(response.content)
                except ET.ParseError:
                    continue
                
                namespaces = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                
                # Check for sitemap index
                if root.tag.endswith('sitemapindex'):
                    for sitemap_node in root.findall('s:sitemap', namespaces):
                        loc = sitemap_node.find('s:loc', namespaces)
                        if loc is not None and loc.text:
                            sitemaps_to_process.append(loc.text.strip())
                            
                # Check for standard urlset
                elif root.tag.endswith('urlset'):
                    for url_node in root.findall('s:url', namespaces):
                        loc = url_node.find('s:loc', namespaces)
                        if loc is not None and loc.text:
                            found_urls.add(loc.text.strip())
                            
        return {
            "status": "success",
            "url_count": len(found_urls),
            "urls": sorted(list(found_urls))
        }
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
