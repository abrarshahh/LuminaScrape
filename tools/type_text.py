import asyncio
import random
from playwright.async_api import Page
from typing import Dict

async def type_text(page: Page, selector: str, text: str, delay: bool = True) -> Dict:
    """
    Types text into an input field identified by a selector.
    
    Args:
        page: The Playwright Page object.
        selector: CSS/XPath selector for the input field.
        text: The text to type.
        delay: Whether to use human-like typing delays between characters.
        
    Returns:
        Dict: Status of the operation.
    """
    try:
        locator = page.locator(selector)
        if await locator.count() == 0:
            return {"status": "failed", "reason": f"Selector '{selector}' not found"}

        element = locator.first
        await element.scroll_into_view_if_needed()
        await element.click() # Ensure focus
        
        if delay:
            # Type character by character with random delays
            for char in text:
                await element.type(char, delay=random.randint(50, 200))
        else:
            await element.fill(text)
            
        return {"status": "success", "selector": selector, "length": len(text)}
        
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
