import asyncio
from playwright.async_api import Page
from typing import Dict, Literal

async def scroll_page(page: Page, direction: Literal["top", "bottom", "down", "up"] = "down", amount: int = 500) -> Dict:
    """
    Scrolls the page in a specified direction.
    
    Args:
        page: The Playwright Page object.
        direction: "top", "bottom", "down", or "up".
        amount: Number of pixels to scroll if direction is "down" or "up".
        
    Returns:
        Dict: Status and current scroll position.
    """
    try:
        if direction == "bottom":
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif direction == "top":
            await page.evaluate("window.scrollTo(0, 0)")
        elif direction == "down":
            await page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            await page.evaluate(f"window.scrollBy(0, -{amount})")
            
        # Wait for lazy-loaded content to trigger
        await asyncio.sleep(1)
        
        scroll_y = await page.evaluate("window.scrollY")
        return {"status": "success", "direction": direction, "scroll_y": scroll_y}
        
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
