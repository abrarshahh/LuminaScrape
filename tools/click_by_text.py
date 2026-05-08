from __future__ import annotations

from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from core.logger import get_logger

logger = get_logger(__name__)


async def click_by_text(page: Page, text: str, *, partial: bool = True, timeout_ms: int = 10_000) -> Dict[str, Any]:
    """
    Click an element containing visible `text`.

    Strategy (inspired by Helping_Files/url_agent.py):
    - Prefer Playwright text locators (fast, robust)
    - Fall back to XPath for partial matches
    - Return visible clickable alternatives on failure (helps LLM choose next action)
    """
    target = (text or "").strip()
    if not target:
        return {"status": "failed", "reason": "Empty text"}

    try:
        # Prefer built-in text engine
        locator = page.get_by_text(target, exact=not partial)
        count = await locator.count()
        if count > 0:
            el = locator.first
            await el.scroll_into_view_if_needed()
            await el.click(timeout=timeout_ms)
            return {"status": "success", "clicked_text": target, "strategy": "get_by_text"}
    except Exception:
        pass

    # XPath fallback
    try:
        t = target.lower()
        if partial:
            xpath = (
                "//*/text()[contains(translate(normalize-space(.),"
                " 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),"
                f" '{t}')]/.."
            )
        else:
            xpath = (
                "//*/text()[translate(normalize-space(.),"
                " 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') ="
                f" '{t}']/.."
            )

        locator = page.locator(f"xpath={xpath}")
        if await locator.count() > 0:
            el = locator.first
            await el.scroll_into_view_if_needed()
            await el.click(timeout=timeout_ms)
            return {"status": "success", "clicked_text": target, "strategy": "xpath"}
    except Exception as e:
        logger.debug(f"click_by_text XPath failed: {e}")

    # Alternatives
    visible_elements: List[Dict[str, Optional[str]]] = []
    try:
        candidates = await page.locator("a, button, [role=button], [role=link]").all()
        for el in candidates[:200]:
            try:
                if await el.is_visible():
                    label = (await el.inner_text()) or ""
                    label = label.strip()
                    href = await el.get_attribute("href")
                    if label:
                        visible_elements.append({"text": label, "href": href})
            except Exception:
                continue
    except Exception:
        pass

    return {
        "status": "failed",
        "reason": f"No element found with text '{target}'",
        "visible_elements": visible_elements,
    }

