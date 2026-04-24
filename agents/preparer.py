from core.llm import LLMProvider
from tools.visit_url import visit_url
from tools.bypass_cloudflare import bypass_cloudflare
from tools.solve_recaptcha import solve_recaptcha
from tools.solve_hcaptcha import solve_hcaptcha
from tools.accept_cookies import accept_cookies
from tools.clean_dom import clean_dom
from core.state import AgentState
from core.logger import get_logger, log_agent_interaction

logger = get_logger(__name__)

class PreparerAgent:
    def __init__(self):
        self.llm = LLMProvider("pilot") 

    async def run(self, state: AgentState, page):
        """
        Visits the URL and cleans up any blockades (Captcha, Cloudflare, etc.)
        """
        url = state["url"]
        task_id = state.get("task_id", "UNKNOWN")
        
        logger.info(f"[{task_id}] Preparer: Visiting {url}")
        
        # 1. Visit the URL
        result = await visit_url(page, url)
        if result["status"] == "failed":
            error_msg = f"Failed to visit URL: {result['reason']}"
            logger.error(f"[{task_id}] Preparer: {error_msg}")
            return {"messages": [{"role": "system", "content": error_msg}]}

        # 2. Check and handle Cloudflare
        logger.debug(f"[{task_id}] Preparer: Checking for Cloudflare")
        await bypass_cloudflare(page)
        
        # 3. Check for Cookie banners
        logger.debug(f"[{task_id}] Preparer: Handling cookies")
        await accept_cookies(page)
        
        # 4. Handle Captchas
        content = await page.content()
        if "g-recaptcha" in content:
            logger.info(f"[{task_id}] Preparer: ReCaptcha detected")
            await solve_recaptcha(page)
        elif "h-captcha" in content:
            logger.info(f"[{task_id}] Preparer: HCaptcha detected")
            await solve_hcaptcha(page)

        # 5. Clean DOM
        logger.debug(f"[{task_id}] Preparer: Cleaning DOM")
        await clean_dom(page)

        log_agent_interaction("Preparer", task_id, f"Prepare {url}", "Webpage prepared and cleaned.")
        
        return {
            "messages": [{"role": "system", "content": "Webpage prepared and cleaned."}],
            "page_metadata": {"url": page.url, "prepared": True}
        }
