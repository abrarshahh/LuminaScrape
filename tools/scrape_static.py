import httpx
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

async def scrape_static(url: str, selectors: Optional[List[str]] = None) -> Dict:
    """
    Performs a simple HTTP GET request to fetch and parse the HTML content of a page.
    Does not execute JavaScript. Useful for sites that block headless browsers or 
    crawlers but allow standard requests.
    
    Args:
        url: The target URL.
        selectors: Optional list of CSS selectors to extract specific data.
        
    Returns:
        Dict: Status and extracted text or HTML content.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return {"status": "failed", "reason": f"HTTP {response.status_code}", "url": url}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            extracted_data = {}
            if selectors:
                for selector in selectors:
                    elements = soup.select(selector)
                    extracted_data[selector] = [el.get_text(strip=True) for el in elements]
            else:
                # Default: extract title and all paragraphs
                extracted_data["title"] = soup.title.string if soup.title else "N/A"
                extracted_data["paragraphs"] = [p.get_text(strip=True) for p in soup.find_all('p')]

            return {
                "status": "success",
                "url": url,
                "data": extracted_data,
                "full_text": soup.get_text(separator=' ', strip=True)[:5000] # Cap text length
            }
            
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
