from playwright.async_api import Page
from typing import Dict

async def get_accessibility_tree(page: Page) -> Dict:
    """
    Retrieves the accessibility tree snapshot of the current page.
    This provides a simplified view of the page structure, which is often 
    better for LLMs than raw HTML.
    
    Args:
        page: The Playwright Page object.
        
    Returns:
        Dict: Status and the accessibility tree snapshot.
    """
    try:
        # Snapshot of the full page AXTree
        ax_tree = await page.accessibility.snapshot()
        
        return {"status": "success", "accessibility_tree": ax_tree}
        
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
