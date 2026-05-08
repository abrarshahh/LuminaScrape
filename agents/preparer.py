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
        Visits the URL and ensures the page is stable, visible, and ready for crawling/extraction.
        This is intentionally "general web hardening" (no site-specific logic).
        """
        url = state["url"]
        task_id = state.get("task_id", "UNKNOWN")
        
        logger.info(f"[{task_id}] Preparer: Visiting {url}")
        
        # 1. Visit the URL (with redirect/region hints)
        result = await visit_url(page, url, wait_until="domcontentloaded", timeout=90000)
        if result["status"] == "failed":
            error_msg = f"Failed to visit URL: {result['reason']}"
            logger.error(f"[{task_id}] Preparer: {error_msg}")
            return {"messages": [{"role": "system", "content": error_msg}]}

        # 2. Stabilize: wait for the page to have meaningful content.
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception:
            pass
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        try:
            await page.wait_for_function(
                "() => document.body && document.body.innerText && document.body.innerText.trim().length > 0",
                timeout=20000,
            )
        except Exception:
            # Some pages intentionally render minimal text; don't hard-fail here.
            pass

        # 3. Blockade busting loop: Cloudflare -> cookies -> captchas -> re-check.
        cloudflare_result = {}
        captcha_result = {}
        cookies_clicked = False

        for _ in range(2):
            logger.debug(f"[{task_id}] Preparer: Checking for Cloudflare")
            cloudflare_result = await bypass_cloudflare(page)
            if cloudflare_result.get("status") in {"blocked", "error"}:
                # If blocked, stop early (extraction won't work).
                reason = cloudflare_result.get("reason") or cloudflare_result.get("status")
                error_msg = f"Blocked by Cloudflare challenge: {reason}"
                logger.warning(f"[{task_id}] Preparer: {error_msg}")
                return {"messages": [{"role": "system", "content": error_msg}], "page_metadata": {"url": page.url, "prepared": False}}

            logger.debug(f"[{task_id}] Preparer: Handling cookies")
            cookies_clicked = await accept_cookies(page) or cookies_clicked

            # Captcha detection + solve (best-effort)
            try:
                content = await page.content()
            except Exception:
                content = ""

            if "g-recaptcha" in content or "recaptcha" in content.lower():
                logger.info(f"[{task_id}] Preparer: ReCaptcha detected")
                captcha_result = await solve_recaptcha(page)
                if captcha_result.get("status") != "success":
                    reason = str(captcha_result.get("reason", ""))
                    if "CAPSOLVER_API_KEY not set" in reason:
                        logger.info(f"[{task_id}] Preparer: ReCaptcha skipped (solver key not configured).")
                    else:
                        logger.warning(f"[{task_id}] Preparer: ReCaptcha not solved: {captcha_result}")
            elif "h-captcha" in content or "hcaptcha" in content.lower():
                logger.info(f"[{task_id}] Preparer: HCaptcha detected")
                captcha_result = await solve_hcaptcha(page)
                if captcha_result.get("status") != "success":
                    reason = str(captcha_result.get("reason", ""))
                    if "CAPSOLVER_API_KEY not set" in reason:
                        logger.info(f"[{task_id}] Preparer: HCaptcha skipped (solver key not configured).")
                    else:
                        logger.warning(f"[{task_id}] Preparer: HCaptcha not solved: {captcha_result}")

            # After interactions/solves, let the page settle again
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

        # 4. Clean DOM (safe defaults; keep iframes unless you explicitly want them removed)
        logger.debug(f"[{task_id}] Preparer: Cleaning DOM")
        await clean_dom(page, remove_iframes=False)

        # 5. Final readiness check
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        try:
            await page.wait_for_function(
                "() => document.body && document.body.innerText !== null",
                timeout=10000,
            )
        except Exception:
            pass

        log_agent_interaction("Preparer", task_id, f"Prepare {url}", "Webpage prepared and cleaned.")
        
        return {
            "messages": [{"role": "system", "content": "Webpage prepared and cleaned."}],
            "page_metadata": {
                "url": page.url,
                "prepared": True,
                "region_redirect": result.get("region_redirect", False),
                "region_redirect_hops": result.get("region_redirect_hops", 0),
                "region_redirect_final_url": result.get("region_redirect_final_url"),
                "cloudflare": cloudflare_result,
                "cookies_clicked": cookies_clicked,
                "captcha": captcha_result,
            },
        }
