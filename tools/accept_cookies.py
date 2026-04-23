from playwright.async_api import Page
from typing import Dict

# Common text patterns and selectors for cookie consent buttons
COOKIE_SELECTORS = [
    "button:has-text('Accept')",
    "button:has-text('Agree')",
    "button:has-text('Allow all')",
    "button:has-text('OK')",
    "button:has-text('I accept')",
    "button:has-text('Accept all cookies')",
    "#onetrust-accept-btn-handler",
    ".cookie-banner__accept",
    "[aria-label='Accept cookies']",
]

async def accept_cookies(page: Page) -> Dict:
    """
    Attempts to identify and click common 'Accept Cookies' buttons.
    
    Args:
        page: The Playwright Page object.
        
    Returns:
        Dict: Status and whether a button was clicked.
    """
    try:
        clicked_any = False
        for selector in COOKIE_SELECTORS:
            locator = page.locator(selector)
            if await locator.count() > 0:
                # Try to click each match (sometimes there are multiple layers)
                for i in range(await locator.count()):
                    el = locator.nth(i)
                    if await el.is_visible():
                        await el.click()
                        clicked_any = True
        
        if clicked_any:
            return {"status": "success", "message": "Cookie banner(s) dismissed"}
        else:
            return {"status": "failed", "reason": "No common cookie banners found"}
            
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
