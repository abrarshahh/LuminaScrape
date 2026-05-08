from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from playwright.async_api import Page

from core.llm import LLMProvider
from core.logger import get_logger, log_agent_interaction
from core.state import AgentState
from tools.auto_scroll_until_stable import auto_scroll_until_stable
from tools.click_by_text import click_by_text
from tools.crawl_page import crawl_page
from tools.extract_page_resources import extract_page_resources
from tools.visit_url import visit_url

logger = get_logger(__name__)


def _same_domain(a: str, b: str) -> bool:
    try:
        ha = (urlparse(a).hostname or "").lower()
        hb = (urlparse(b).hostname or "").lower()
        if not ha or not hb:
            return False
        return ha == hb or ha.endswith("." + hb) or hb.endswith("." + ha)
    except Exception:
        return False


class NavigatorAgent:
    """
    Ensures we are on the right page for the user's prompt.

    It decides whether to:
    - extract now
    - scroll more (lazy loading)
    - navigate within site (click by text or go to an internal URL)
    - stop if blocked/login
    """

    def __init__(self):
        self.llm = LLMProvider("navigator")

    async def run(self, state: AgentState, page: Page) -> Dict[str, Any]:
        task_id = state.get("task_id", "UNKNOWN")
        prompt = state["prompt"]
        schema = state.get("schema")
        start_url = state.get("url")

        max_steps = int(os.getenv("MAX_NAVIGATION_STEPS", "6"))
        max_links = int(os.getenv("NAVIGATION_LINK_LIMIT", "80"))

        base_url = page.url

        for step in range(1, max_steps + 1):
            logger.info(f"[{task_id}] Navigator: step {step}/{max_steps} on {page.url}")

            # Build context cheaply
            title = ""
            try:
                title = await page.title()
            except Exception:
                pass

            crawl = await crawl_page(page)
            text = (crawl.get("markdown") or "")[:8000]
            resources = await extract_page_resources(page, max_items=max_links)

            # Compress links: keep only anchor-type with text
            link_summaries: List[Dict[str, Any]] = []
            for r in resources:
                if r.get("type") in {"html", "pdf"}:
                    t = (r.get("text") or "").strip()
                    u = r.get("url")
                    if not u:
                        continue
                    if t:
                        link_summaries.append({"text": t[:120], "url": u})
            link_summaries = link_summaries[:max_links]

            system_prompt = f"""
You are a web navigation planner for a scraping agent.
Your job is to decide if the CURRENT PAGE contains the data needed to satisfy the user's request.
If not, choose the smallest next action to reach the correct page efficiently.

USER PROMPT:
{prompt}

OPTIONAL TARGET SCHEMA (shape to extract):
{json.dumps(schema) if schema else "null"}

CURRENT PAGE:
- url: {page.url}
- title: {title}

VISIBLE TEXT (truncated):
{text}

VISIBLE LINKS (text + url, truncated):
{json.dumps(link_summaries)[:8000]}

Return ONLY JSON in this format:
{{
  "action": "extract_now" | "scroll_more" | "navigate_url" | "click_text" | "stop",
  "reason": "short reason",
  "confidence": 0.0,
  "target_url": "only if action=navigate_url",
  "click_text": "only if action=click_text",
  "scroll_steps": 0
}}

RULES:
- If data likely present on page: action=extract_now.
- If page looks like list/feed and more items are needed: action=scroll_more with scroll_steps 3-12.
- If links suggest the correct section (e.g. Trending/News/Products/Search): action=click_text OR navigate_url.
- Only navigate within the same domain as the current page.
- If login/paywall/captcha blocks access: action=stop.
"""

            messages = [{"role": "system", "content": system_prompt}]
            response = await asyncio.to_thread(self.llm.call, messages, {"type": "json_object"})
            if not response:
                return {"navigation": {"status": "failed", "reason": "Navigator LLM did not respond"}}

            try:
                plan = json.loads(response.choices[0].message.content)
            except Exception as e:
                return {"navigation": {"status": "failed", "reason": f"Navigator JSON parse error: {e}"}}

            action = (plan.get("action") or "").strip()
            reason = plan.get("reason") or ""
            confidence = float(plan.get("confidence") or 0.0)

            logger.info(f"[{task_id}] Navigator decision: {action} (conf={confidence}) reason={reason}")

            if action == "extract_now":
                log_agent_interaction("Navigator", task_id, f"Navigate for: {prompt}", f"Extract now: {reason}")
                return {"navigation": {"status": "ready", "action": "extract_now", "reason": reason, "confidence": confidence}}

            if action == "scroll_more":
                steps = int(plan.get("scroll_steps") or 6)
                steps = max(1, min(steps, 25))
                await auto_scroll_until_stable(page, max_steps=steps)
                continue

            if action == "click_text":
                txt = (plan.get("click_text") or "").strip()
                if not txt:
                    return {"navigation": {"status": "failed", "reason": "Navigator asked to click_text but provided no click_text"}}
                res = await click_by_text(page, txt, partial=True)
                if res.get("status") != "success":
                    # Give the model one more chance next iteration; it will see updated links and can choose navigate_url.
                    logger.warning(f"[{task_id}] Navigator click failed: {res.get('reason')}")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                except Exception:
                    pass
                continue

            if action == "navigate_url":
                target_url = (plan.get("target_url") or "").strip()
                if not target_url:
                    return {"navigation": {"status": "failed", "reason": "Navigator asked to navigate_url but provided no target_url"}}
                if not _same_domain(page.url, target_url):
                    return {"navigation": {"status": "failed", "reason": "Navigator target_url is off-domain; refusing"}}
                nav = await visit_url(page, target_url, wait_until="domcontentloaded", timeout=90000)
                if nav.get("status") != "success":
                    return {"navigation": {"status": "failed", "reason": f"Failed navigating: {nav.get('reason')}"}}
                continue

            # stop or unknown
            log_agent_interaction("Navigator", task_id, f"Navigate for: {prompt}", f"Stop: {reason}")
            return {"navigation": {"status": "stopped", "action": "stop", "reason": reason, "confidence": confidence}}

        return {"navigation": {"status": "max_steps_reached", "reason": f"Reached {max_steps} navigation steps"}}

