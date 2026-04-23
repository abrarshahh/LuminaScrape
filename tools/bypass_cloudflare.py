import asyncio
from playwright.async_api import Page
from typing import Dict

async def bypass_cloudflare(page: Page, timeout: int = 30000) -> Dict:
    """
    Attempts to bypass Cloudflare 'Waiting' or 'Verify' pages.
    Detects the presence of Cloudflare challenges and waits for them to resolve 
    or attempts to interact with the verification checkbox.
    
    Args:
        page: The Playwright Page object.
        timeout: Maximum time to wait for the bypass.
        
    Returns:
        Dict: Status of the bypass attempt.
    """
    try:
        # 1. Detect Cloudflare
        content = await page.content()
        if "cf-challenge" not in content and "Checking your browser" not in content:
            return {"status": "success", "message": "No Cloudflare challenge detected"}

        # 2. Wait for challenge to resolve automatically (many do with stealth)
        try:
            # Wait for the challenge div to disappear or the page to redirect
            await page.wait_for_selector(".cf-challenge", state="hidden", timeout=timeout)
            return {"status": "success", "message": "Cloudflare challenge resolved automatically"}
        except:
            pass

        # 3. Try to click the "Verify you are human" checkbox if visible
        # This is a common pattern for Turnstile
        try:
            checkbox = page.locator("iframe[src*='challenges.cloudflare.com']").content_frame.locator("#challenge-stage")
            if await checkbox.count() > 0:
                await checkbox.click()
                await asyncio.sleep(5) # Wait for redirect
                return {"status": "success", "message": "Cloudflare checkbox clicked"}
        except:
            pass

        return {"status": "failed", "reason": "Cloudflare bypass timed out or failed"}
        
    except Exception as e:
        return {"status": "failed", "reason": str(e)}
