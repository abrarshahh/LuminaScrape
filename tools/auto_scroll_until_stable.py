from __future__ import annotations

import asyncio
from typing import Dict, Any

from playwright.async_api import Page

from core.logger import get_logger

logger = get_logger(__name__)


async def _page_text_len(page: Page) -> int:
    try:
        return int(
            await page.evaluate(
                "() => (document.body && document.body.innerText) ? document.body.innerText.length : 0"
            )
        )
    except Exception:
        return 0


async def _doc_height(page: Page) -> int:
    try:
        return int(
            await page.evaluate(
                "() => Math.max(document.body?.scrollHeight || 0, document.documentElement?.scrollHeight || 0)"
            )
        )
    except Exception:
        return 0


async def auto_scroll_until_stable(
    page: Page,
    *,
    step_px: int = 800,
    max_steps: int = 20,
    wait_ms: int = 800,
    stable_rounds: int = 3,
) -> Dict[str, Any]:
    """
    Scrolls down in steps and stops when content appears stable.

    Stability heuristic:
    - document height and visible text length stop increasing for `stable_rounds` iterations.
    """
    logger.info(f"Auto-scroll until stable (max_steps={max_steps}, step_px={step_px})")

    stable = 0
    last_height = await _doc_height(page)
    last_text = await _page_text_len(page)

    for i in range(1, max_steps + 1):
        try:
            await page.evaluate("(y) => window.scrollBy(0, y)", step_px)
        except Exception:
            break

        try:
            await page.wait_for_timeout(wait_ms)
        except Exception:
            await asyncio.sleep(wait_ms / 1000)

        h = await _doc_height(page)
        t = await _page_text_len(page)

        grew = (h > last_height) or (t > last_text + 50)
        last_height, last_text = h, t

        if not grew:
            stable += 1
        else:
            stable = 0

        if stable >= stable_rounds:
            logger.info(f"Auto-scroll stabilized after {i} steps.")
            return {"status": "success", "steps": i, "stable": True, "height": h, "text_len": t}

    logger.info("Auto-scroll reached max steps or stopped.")
    return {"status": "success", "steps": max_steps, "stable": False, "height": last_height, "text_len": last_text}

