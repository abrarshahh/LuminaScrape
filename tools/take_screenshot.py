import os
from datetime import datetime
from playwright.async_api import Page
from typing import Dict

async def take_screenshot(page: Page, full_page: bool = False, prefix: str = "screenshot") -> Dict:
    """
    Captures a screenshot of the current page.
    
    Args:
        page: The Playwright Page object.
        full_page: Whether to capture the entire scrollable page or just the viewport.
        prefix: Prefix for the filename.
        
    Returns:
        Dict: Status and file path.
    """
    try:
        # Ensure screenshots directory exists
        screenshot_dir = os.path.abspath("screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        
        filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        file_path = os.path.join(screenshot_dir, filename)
        
        await page.screenshot(path=file_path, full_page=full_page)
        
        return {"status": "success", "file_path": file_path, "full_page": full_page}
        
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
