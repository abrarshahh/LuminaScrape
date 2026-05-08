import os
import sys
from typing import Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv


def fetch_groq_models(api_key: str) -> List[str]:
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    models = [m.get("id") for m in data.get("data", []) if m.get("id")]
    return sorted(models)


def _extract_rate_limits(headers: httpx.Headers) -> Dict[str, Optional[str]]:
    return {
        "requests_limit": headers.get("x-ratelimit-limit-requests"),
        "requests_remaining": headers.get("x-ratelimit-remaining-requests"),
        "tokens_limit": headers.get("x-ratelimit-limit-tokens"),
        "tokens_remaining": headers.get("x-ratelimit-remaining-tokens"),
        "reset_requests": headers.get("x-ratelimit-reset-requests"),
        "reset_tokens": headers.get("x-ratelimit-reset-tokens"),
    }


def probe_groq_model(client: httpx.Client, api_key: str, model: str) -> Tuple[bool, Dict[str, Optional[str]], str]:
    """
    Probe model with a tiny completion request.
    Returns: (usable_now, rate_limits, status_reason)
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    try:
        resp = client.post(url, headers=headers, json=payload)
    except Exception as exc:
        return False, {}, f"request_error:{exc}"

    rate_limits = _extract_rate_limits(resp.headers)

    if resp.status_code == 200:
        return True, rate_limits, "ok"

    # Common non-free / quota / auth patterns
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}
    msg = str(body).lower()
    if resp.status_code in (401, 403):
        return False, rate_limits, "unauthorized_or_forbidden"
    if resp.status_code == 429:
        return False, rate_limits, "rate_limited_or_quota_exceeded"
    if "insufficient_quota" in msg or "billing" in msg or "payment" in msg:
        return False, rate_limits, "paid_or_quota_required"
    if "model_not_found" in msg or resp.status_code == 404:
        return False, rate_limits, "not_available_for_key"
    return False, rate_limits, f"http_{resp.status_code}"


def main() -> int:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        print("Missing GROQ_API_KEY in environment/.env")
        return 1

    try:
        models = fetch_groq_models(api_key)
    except Exception as exc:
        print(f"Failed to fetch Groq models: {exc}")
        return 1

    if not models:
        print("No models returned by Groq for this key.")
        return 0

    max_checks = int(os.getenv("MAX_MODEL_CHECKS", "200"))
    models = models[:max_checks]

    free_usable = []
    with httpx.Client(timeout=30) as client:
        for model in models:
            usable, limits, reason = probe_groq_model(client, api_key, model)
            if usable:
                free_usable.append((model, limits))
            # Keep output quiet unless troubleshooting
            # else:
            #     print(f"skip {model}: {reason}")

    if not free_usable:
        print("No currently-usable Groq models detected for this key.")
        return 0

    print("Groq models usable now (free-tier behavior) with rate-limit headers:")
    for model, limits in free_usable:
        req_lim = limits.get("requests_limit") or "unknown"
        tok_lim = limits.get("tokens_limit") or "unknown"
        req_rem = limits.get("requests_remaining") or "unknown"
        tok_rem = limits.get("tokens_remaining") or "unknown"
        print(
            f"- {model} | rpm_limit={req_lim} rpm_remaining={req_rem} "
            f"tpm_limit={tok_lim} tpm_remaining={tok_rem}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

