from __future__ import annotations

import os
import re
import asyncio
from typing import Optional, Dict, Any

import httpx
from playwright.async_api import Page

from core.logger import get_logger

logger = get_logger(__name__)


async def _detect_recaptcha_sitekey(page: Page) -> Optional[str]:
    """
    Best-effort detection of reCAPTCHA sitekey.
    Looks for:
    - <div class="g-recaptcha" data-sitekey="...">
    - iframes with src containing k=<sitekey>
    """
    try:
        sitekey = await page.evaluate(
            """() => {
              const el = document.querySelector('.g-recaptcha[data-sitekey], [data-sitekey].g-recaptcha');
              if (el && el.getAttribute('data-sitekey')) return el.getAttribute('data-sitekey');
              const ifr = Array.from(document.querySelectorAll('iframe[src*="recaptcha"]'));
              for (const f of ifr) {
                try {
                  const u = new URL(f.src);
                  const k = u.searchParams.get('k');
                  if (k) return k;
                } catch {}
              }
              return null;
            }"""
        )
        return sitekey or None
    except Exception:
        return None


async def _capsolver_create_task(api_key: str, website_url: str, sitekey: str) -> Optional[str]:
    """
    Create a CapSolver task for reCAPTCHA v2 (proxyless).
    """
    payload = {
        "clientKey": api_key,
        "task": {
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": website_url,
            "websiteKey": sitekey,
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.capsolver.com/createTask", json=payload)
        r.raise_for_status()
        data = r.json()
        task_id = data.get("taskId")
        return str(task_id) if task_id else None


async def _capsolver_poll_result(api_key: str, task_id: str, *, max_wait_s: int = 120) -> Optional[str]:
    start = asyncio.get_event_loop().time()
    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            r = await client.post("https://api.capsolver.com/getTaskResult", json={"clientKey": api_key, "taskId": task_id})
            r.raise_for_status()
            data: Dict[str, Any] = r.json()
            if data.get("status") == "ready":
                sol = (data.get("solution") or {}).get("gRecaptchaResponse")
                return sol or None
            if asyncio.get_event_loop().time() - start > max_wait_s:
                return None
            await asyncio.sleep(2)


async def _inject_recaptcha_token(page: Page, token: str) -> bool:
    """
    Inject token into common reCAPTCHA response fields.
    Many sites read `textarea[name="g-recaptcha-response"]`.
    """
    try:
        await page.evaluate(
            """(tok) => {
              const areas = Array.from(document.querySelectorAll('textarea[name="g-recaptcha-response"], textarea#g-recaptcha-response'));
              for (const ta of areas) {
                ta.value = tok;
                ta.innerHTML = tok;
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                ta.dispatchEvent(new Event('change', { bubbles: true }));
              }
              // Some implementations store on a hidden input
              const inputs = Array.from(document.querySelectorAll('input[name="g-recaptcha-response"]'));
              for (const i of inputs) {
                i.value = tok;
                i.dispatchEvent(new Event('input', { bubbles: true }));
                i.dispatchEvent(new Event('change', { bubbles: true }));
              }
              return areas.length + inputs.length;
            }""",
            token,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to inject reCAPTCHA token: {e}")
        return False


async def solve_recaptcha(page: Page) -> Dict[str, Any]:
    """
    Solve reCAPTCHA v2 using an optional provider (CapSolver).

    Environment:
    - CAPTCHA_PROVIDER=capsolver
    - CAPSOLVER_API_KEY=...
    """
    logger.info("Tool: ReCaptcha detected. Attempting solve...")

    provider = (os.getenv("CAPTCHA_PROVIDER") or "capsolver").strip().lower()
    if provider != "capsolver":
        return {"status": "failed", "reason": f"Unsupported CAPTCHA_PROVIDER '{provider}'"}

    api_key = os.getenv("CAPSOLVER_API_KEY")
    if not api_key:
        return {"status": "failed", "reason": "CAPSOLVER_API_KEY not set (captcha solver not configured)"}

    sitekey = await _detect_recaptcha_sitekey(page)
    if not sitekey:
        # The page might still have recaptcha but hidden; we avoid claiming success.
        return {"status": "failed", "reason": "Could not detect reCAPTCHA sitekey on page"}

    website_url = page.url
    try:
        task_id = await _capsolver_create_task(api_key, website_url, sitekey)
        if not task_id:
            return {"status": "failed", "reason": "CapSolver did not return a taskId"}

        token = await _capsolver_poll_result(api_key, task_id)
        if not token:
            return {"status": "failed", "reason": "CapSolver did not return a token in time"}

        ok = await _inject_recaptcha_token(page, token)
        return {"status": "success" if ok else "failed", "provider": "capsolver", "sitekey": sitekey}
    except Exception as e:
        logger.error(f"reCAPTCHA solve failed: {e}")
        return {"status": "failed", "reason": str(e)}
