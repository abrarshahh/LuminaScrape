from playwright.async_api import Page
from typing import Dict

async def clean_dom(page: Page) -> Dict:
    """
    Removes non-essential elements from the DOM to reduce noise and token usage.
    Strips scripts, styles, iframes, ads, and hidden elements.
    
    Args:
        page: The Playwright Page object.
        
    Returns:
        Dict: Status and summary of elements removed.
    """
    try:
        # JavaScript to clean the DOM
        stats = await page.evaluate("""
            () => {
                const selectors = [
                    'script', 'style', 'iframe', 'noscript', 'header', 'footer', 'nav', 
                    '[role="banner"]', '[role="contentinfo"]', '.ads', '.advertisement', 
                    '#cookie-banner', '.cookie-consent'
                ];
                
                let count = 0;
                selectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    count += elements.length;
                    elements.forEach(el => el.remove());
                });
                
                // Also remove hidden elements
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') {
                        el.remove();
                        count++;
                    }
                });
                
                return { elements_removed: count };
            }
        """)
        
        return {"status": "success", "stats": stats}
        
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
