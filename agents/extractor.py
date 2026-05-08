from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Union, Tuple

from core.llm import LLMProvider
from core.state import AgentState
from core.logger import get_logger, log_agent_interaction
from tools.get_accessibility_tree import get_accessibility_tree
from tools.crawl_page import crawl_page
from tools.extract_page_resources import extract_page_resources
from tools.auto_scroll_until_stable import auto_scroll_until_stable
from tools.visit_url import visit_url

logger = get_logger(__name__)


Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def _normalize_to_schema_template(schema: Any, data: Any) -> Any:
    """
    Best-effort coercion to match a schema TEMPLATE like:
      { "meta": {...}, "data": [ { ... } ] }
    We do not enforce JSON Schema; we simply ensure keys/shape exist.
    """
    if schema is None:
        return data

    # Template is a dict: ensure all keys exist.
    if isinstance(schema, dict):
        if not isinstance(data, dict):
            data = {}
        out: Dict[str, Any] = {}
        for k, v in schema.items():
            if k in data:
                out[k] = _normalize_to_schema_template(v, data.get(k))
            else:
                # Fill with empty structure based on template
                out[k] = _normalize_to_schema_template(v, None)
        # Keep extra keys (sometimes useful) but avoid exploding output.
        for k in data.keys():
            if k not in out:
                out[k] = data[k]
        return out

    # Template is a list: treat as homogeneous list with example element at [0].
    if isinstance(schema, list):
        template_item = schema[0] if schema else None
        if not isinstance(data, list):
            # If data is a dict and template expects list of objects, wrap
            if isinstance(data, dict):
                return [_normalize_to_schema_template(template_item, data)]
            return []
        return [_normalize_to_schema_template(template_item, item) for item in data]

    # Template is a placeholder type string ("string", "number"...). Leave as-is but allow None.
    if data is None:
        return None
    return data


def _schema_primary_template(schema: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    If schema is in our preferred format, return a template object for normalization.
    """
    if not schema or not isinstance(schema, dict):
        return None
    return schema


def _is_type_placeholder(x: Any) -> bool:
    return isinstance(x, str) and x.strip().lower() in {"string", "number", "boolean", "date", "url", "object", "array"}


def _validate_types(template: Any, value: Any, path: str = "$") -> List[str]:
    """
    Validate extracted data against a template that uses placeholder types.
    - Allows null for any field.
    - Enforces arrays vs objects vs primitives.
    """
    errors: List[str] = []

    if value is None:
        return errors

    # Dict template
    if isinstance(template, dict):
        if not isinstance(value, dict):
            return [f"{path}: expected object"]
        for k, tv in template.items():
            if k not in value:
                errors.append(f"{path}.{k}: missing key")
            else:
                errors.extend(_validate_types(tv, value.get(k), f"{path}.{k}"))
        return errors

    # List template
    if isinstance(template, list):
        if not isinstance(value, list):
            return [f"{path}: expected array"]
        item_t = template[0] if template else None
        for i, item in enumerate(value[:200]):  # cap
            errors.extend(_validate_types(item_t, item, f"{path}[{i}]"))
        return errors

    # Placeholder string template
    if _is_type_placeholder(template):
        t = template.strip().lower()
        if t == "string":
            if not isinstance(value, str):
                errors.append(f"{path}: expected string")
        elif t == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{path}: expected number")
        elif t == "boolean":
            if not isinstance(value, bool):
                errors.append(f"{path}: expected boolean")
        elif t == "url":
            if not isinstance(value, str) or not (value.startswith("http://") or value.startswith("https://")):
                errors.append(f"{path}: expected url string")
        elif t == "date":
            if not isinstance(value, str):
                errors.append(f"{path}: expected date string")
        elif t == "object":
            if not isinstance(value, dict):
                errors.append(f"{path}: expected object")
        elif t == "array":
            if not isinstance(value, list):
                errors.append(f"{path}: expected array")
        return errors

    return errors


def _desired_count_from_schema(schema: Optional[Dict[str, Any]]) -> Optional[int]:
    try:
        if not schema or not isinstance(schema, dict):
            return None
        meta = schema.get("meta")
        if not isinstance(meta, dict):
            return None
        c = meta.get("count") or meta.get("top_n") or meta.get("limit")
        if isinstance(c, int):
            return max(1, c)
        if isinstance(c, str) and c.isdigit():
            return max(1, int(c))
        return None
    except Exception:
        return None


async def _select_detail_urls(
    llm: LLMProvider,
    prompt: str,
    current_url: str,
    candidates: List[Dict[str, str]],
    *,
    max_urls: int,
) -> List[str]:
    selector_prompt = f"""
You select the best detail-page URLs to extract the user's requested data.

USER PROMPT:
{prompt}

CURRENT URL:
{current_url}

CANDIDATE LINKS (text,url):
{json.dumps(candidates)[:12000]}

Return ONLY JSON:
{{"urls": ["https://..."]}}

Rules:
- Choose up to {max_urls} URLs.
- Prefer URLs that likely contain the detailed data requested.
- Avoid category pages, login, privacy/terms, mailto, and duplicates.
"""
    resp = await asyncio.to_thread(llm.call, [{"role": "system", "content": selector_prompt}], {"type": "json_object"})
    if not resp:
        return []
    try:
        data = json.loads(resp.choices[0].message.content)
        urls = data.get("urls") or []
        if not isinstance(urls, list):
            return []
        out: List[str] = []
        for u in urls:
            if isinstance(u, str) and u.startswith(("http://", "https://")):
                out.append(u)
        # de-dupe preserve order
        seen = set()
        dedup = []
        for u in out:
            if u in seen:
                continue
            seen.add(u)
            dedup.append(u)
        return dedup[:max_urls]
    except Exception:
        return []


class ExtractorAgent:
    def __init__(self):
        self.llm = LLMProvider("extractor")
        self.selector_llm = LLMProvider("multipage_selector")

    async def run(self, state: AgentState, page):
        """
        Extracts structured data from the page markdown and AXTree.
        """
        prompt = state["prompt"]
        schema = state.get("schema")
        task_id = state.get("task_id", "UNKNOWN")
        feedback = state.get("feedback", "")
        step_count = state.get("step_count", 0)
        page_metadata = state.get("page_metadata") or {}
        navigation = state.get("navigation") or {}
        
        logger.info(f"[{task_id}] Extractor: Starting extraction for prompt: {prompt}")

        # 1. Get Page Context
        logger.debug(f"[{task_id}] Extractor: Gathering page context (Markdown + AXTree)")
        crawl_result = await crawl_page(page)
        markdown = crawl_result.get("markdown", "") or ""
        crawl4ai_markdown = crawl_result.get("crawl4ai_markdown")
        
        ax_tree = await get_accessibility_tree(page)
        
        # 2. Build LLM Prompt
        schema_json = json.dumps(schema) if schema else "null"
        ax_snippet = json.dumps(ax_tree.get("accessibility_tree"))[:4000]
        content_blocks = [
            "You are an expert Data Extraction Agent.",
            "Extract ONLY the information requested by the user from the provided page context.",
            "",
            f"USER PROMPT:\n{prompt}",
            "",
            f"CURRENT URL:\n{page.url}",
            "",
            f"PAGE METADATA (preparer):\n{json.dumps(page_metadata)[:2000]}",
            "",
            f"NAVIGATION DECISION:\n{json.dumps(navigation)[:2000]}",
            "",
        ]

        if feedback and step_count > 0:
            content_blocks += [
                "IMPORTANT: This is a retry. Fix the issues described by the validator.",
                f"VALIDATOR FEEDBACK:\n{feedback}",
                "",
            ]

        content_blocks += [
            "CONTEXT (AXTree Snapshot, truncated):",
            ax_snippet,
            "",
            "CONTENT (Visible text / markdown, truncated):",
            markdown[:12000],
        ]

        if crawl4ai_markdown:
            content_blocks += [
                "",
                "CONTENT (crawl4ai markdown, truncated):",
                str(crawl4ai_markdown)[:12000],
            ]

        content_blocks += [
            "",
            "OUTPUT REQUIREMENTS:",
            "- Return ONLY a valid JSON object.",
            "- Do NOT include explanations.",
            "- If a field is unknown, use null (not invented values).",
        ]

        if schema:
            content_blocks += [
                "",
                "STRICT OUTPUT SHAPE TEMPLATE (must match keys/structure):",
                schema_json,
            ]

        system_prompt = "\n".join(content_blocks)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Extract the data now."}
        ]

        # 3. Call LLM
        logger.debug(f"[{task_id}] Extractor: Calling LLM ({self.llm.model_name})")
        response = await asyncio.to_thread(self.llm.call, messages, {"type": "json_object"})
        
        if not response:
            logger.error(f"[{task_id}] Extractor: LLM failed to return a response")
            return {"messages": [{"role": "system", "content": "Extractor: LLM failed to respond."}]}

        try:
            raw = response.choices[0].message.content
            extracted_data: Any = json.loads(raw)
            if not isinstance(extracted_data, dict):
                # We require an object. Wrap in a predictable structure.
                extracted_data = {"data": extracted_data}

            # Best-effort normalization to template schema
            template = _schema_primary_template(schema)
            if template:
                extracted_data = _normalize_to_schema_template(template, extracted_data)

            # Stronger schema/type validation
            validation_errors: List[str] = []
            if template:
                validation_errors = _validate_types(template, extracted_data)

            # One repair attempt if it structurally matches but types/fields are off
            if template and validation_errors:
                repair_prompt = f"""
You are fixing a JSON output to match a required template and types.
Return ONLY corrected JSON.

USER PROMPT:
{prompt}

TEMPLATE:
{json.dumps(template)}

CURRENT OUTPUT:
{json.dumps(extracted_data)[:12000]}

VALIDATION ERRORS:
{json.dumps(validation_errors)[:4000]}
"""
                repair_resp = await asyncio.to_thread(self.llm.call, [{"role": "system", "content": repair_prompt}], {"type": "json_object"})
                if repair_resp:
                    try:
                        repaired = json.loads(repair_resp.choices[0].message.content)
                        if isinstance(repaired, dict):
                            repaired = _normalize_to_schema_template(template, repaired)
                            repaired_errors = _validate_types(template, repaired)
                            if len(repaired_errors) <= len(validation_errors):
                                extracted_data = repaired
                                validation_errors = repaired_errors
                    except Exception:
                        pass

            # Multi-page extraction: fill `data` up to desired count by visiting detail URLs and extracting per-page item.
            desired = _desired_count_from_schema(schema) or None
            if template and desired and isinstance(extracted_data, dict):
                data_list = extracted_data.get("data")
                item_template = None
                if isinstance(template.get("data"), list) and template["data"]:
                    item_template = template["data"][0]
                if item_template and isinstance(data_list, list):
                    if len(data_list) < desired:
                        # Collect candidate links
                        resources = await extract_page_resources(page, max_items=300)
                        candidates: List[Dict[str, str]] = []
                        for r in resources:
                            if r.get("type") != "html":
                                continue
                            u = r.get("url")
                            t = (r.get("text") or "").strip()
                            if not u or not u.startswith(("http://", "https://")):
                                continue
                            if not t or len(t) < 2:
                                continue
                            candidates.append({"text": t[:120], "url": u})
                        candidates = candidates[:150]

                        max_urls = min(10, max(1, desired - len(data_list)))
                        chosen_urls = await _select_detail_urls(self.selector_llm, prompt, page.url, candidates, max_urls=max_urls)

                        # Visit each detail url and extract a single item
                        for u in chosen_urls:
                            if len(data_list) >= desired:
                                break
                            nav = await visit_url(page, u, wait_until="domcontentloaded", timeout=90000)
                            if nav.get("status") != "success":
                                continue
                            # handle lazy load on detail pages too
                            await auto_scroll_until_stable(page, max_steps=10)

                            detail_crawl = await crawl_page(page)
                            detail_text = (detail_crawl.get("markdown") or "")[:10000]
                            detail_ax = await get_accessibility_tree(page)
                            detail_ax_snip = json.dumps(detail_ax.get("accessibility_tree"))[:2000]

                            item_prompt = f"""
Extract ONE item from this detail page relevant to the user prompt.
Return ONLY JSON for ONE item that matches this template:
{json.dumps(item_template)}

USER PROMPT:
{prompt}

URL: {page.url}
AXTREE: {detail_ax_snip}
TEXT: {detail_text}
"""
                            item_resp = await asyncio.to_thread(self.llm.call, [{"role": "system", "content": item_prompt}], {"type": "json_object"})
                            if not item_resp:
                                continue
                            try:
                                item = json.loads(item_resp.choices[0].message.content)
                                if isinstance(item, dict):
                                    item = _normalize_to_schema_template(item_template, item)
                                    # type validation per item
                                    item_errs = _validate_types(item_template, item)
                                    if len(item_errs) < 8:  # allow minor issues
                                        data_list.append(item)
                            except Exception:
                                continue

                        extracted_data["data"] = data_list[:desired]

            logger.info(f"[{task_id}] Extractor: Successfully extracted data")
            
            # Log to agents.log
            log_agent_interaction("Extractor", task_id, prompt, json.dumps(extracted_data, indent=2))
            
            return {
                "extraction_result": extracted_data,
                "extraction_validation_errors": validation_errors if template else [],
                "messages": [{"role": "assistant", "content": "Data extracted successfully."}]
            }
        except Exception as e:
            logger.error(f"[{task_id}] Extractor: Failed to parse LLM response: {e}")
            return {"messages": [{"role": "system", "content": f"Extractor: Parsing error: {e}"}]}
