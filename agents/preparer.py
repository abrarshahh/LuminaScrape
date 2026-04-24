from core.llm import LLMProvider
from tools.visit_url import visit_url
from tools.bypass_cloudflare import bypass_cloudflare
from tools.solve_recaptcha import solve_recaptcha
from tools.solve_hcaptcha import solve_hcaptcha
from tools.accept_cookies import accept_cookies
from tools.clean_dom import clean_dom
from core.state import AgentState

class PreparerAgent:
    def __init__(self):
        self.llm = LLMProvider("pilot") # Using pilot config for preparation

    async def run(self, state: AgentState, page):
        """
        Visits the URL and cleans up any blockades (Captcha, Cloudflare, etc.)
        """
        url = state["url"]
        
        # 1. Visit the URL
        print(f"[Preparer] Visiting {url}...")
        result = await visit_url(page, url)
        if result["status"] == "failed":
            return {"messages": [{"role": "system", "content": f"Failed to visit URL: {result['reason']}"}]}

        # 2. Check and handle Cloudflare
        print("[Preparer] Checking for Cloudflare...")
        cf_result = await bypass_cloudflare(page)
        
        # 3. Check for Cookie banners
        print("[Preparer] Checking for Cookie banners...")
        await accept_cookies(page)
        
        # 4. Handle Captchas (This would be more complex in reality, 
        # usually triggered if the LLM detects a captcha in the state)
        # For now, we do a proactive check
        content = await page.content()
        if "g-recaptcha" in content:
            print("[Preparer] ReCaptcha detected. Attempting to solve...")
            await solve_recaptcha(page)
        elif "h-captcha" in content:
            print("[Preparer] HCaptcha detected. Attempting to solve...")
            await solve_hcaptcha(page)

        # 5. Clean DOM
        print("[Preparer] Cleaning DOM for easier extraction...")
        await clean_dom(page)

        return {
            "messages": [{"role": "system", "content": "Webpage prepared and cleaned."}],
            "page_metadata": {"url": page.url, "prepared": True}
        }
