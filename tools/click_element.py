from playwright.async_api import Page
from typing import Dict, Optional

async def click_element(page: Page, text: Optional[str] = None, selector: Optional[str] = None) -> Dict:
    """
    Clicks an element on the page identified by text or a CSS selector.
    If multiple elements match, it clicks the first visible one.
    
    Args:
        page: The Playwright Page object.
        text: The visible text of the element to click.
        selector: A CSS or XPath selector for the element.
        
    Returns:
        Dict: Status and details of the clicked element.
    """
    if not text and not selector:
        return {"status": "failed", "reason": "Either text or selector must be provided"}

    try:
        locator = None
        if selector:
            locator = page.locator(selector)
        elif text:
            # Normalized XPath search for text
            text_normalized = text.strip().lower()
            xpath_exact = f"//*/text()[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '{text_normalized}']/.."
            xpath_partial = f"//*/text()[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text_normalized}')]/.."
            
            # Try exact match first
            locator = page.locator(f"xpath={xpath_exact}")
            if await locator.count() == 0:
                # Fallback to partial match
                locator = page.locator(f"xpath={xpath_partial}")

        if not locator or await locator.count() == 0:
            # If no element found, try to list visible alternatives (buttons/links)
            candidates = await page.locator("a, button, [role=button], [role=link]").all()
            visible_elements = []
            for el in candidates:
                if await el.is_visible():
                    label = await el.inner_text()
                    if label.strip():
                        visible_elements.append(label.strip())
            
            return {
                "status": "failed", 
                "reason": "Element not found",
                "visible_elements": visible_elements[:10] # Return top 10
            }

        element = locator.first
        await element.scroll_into_view_if_needed()
        await element.click()
        
        return {"status": "success", "clicked_text": text, "selector": selector}
        
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
