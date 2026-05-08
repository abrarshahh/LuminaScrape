from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

from core.llm import LLMProvider
from core.logger import get_logger

logger = get_logger(__name__)


def _normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a predictable top-level schema shape:
      { meta: {...}, data: [ { ... } ] }
    """
    if not isinstance(schema, dict):
        return {"meta": {"notes": "Invalid schema type returned"}, "data": [{}]}

    meta = schema.get("meta")
    if not isinstance(meta, dict):
        meta = {}

    data = schema.get("data")
    if isinstance(data, list) and data:
        # Keep first element as template if list contents are objects; else wrap.
        if not isinstance(data[0], dict):
            data = [{}]
    elif isinstance(data, dict):
        data = [data]
    else:
        # Back-compat: some models return {items:[...]} or {schema:{...}}
        items = schema.get("items")
        if isinstance(items, list) and items and isinstance(items[0], dict):
            data = [items[0]]
        elif isinstance(schema.get("schema"), dict):
            inner = schema["schema"]
            if isinstance(inner.get("data"), list) and inner["data"] and isinstance(inner["data"][0], dict):
                data = [inner["data"][0]]
            else:
                data = [{}]
        else:
            data = [{}]

    schema["meta"] = meta
    schema["data"] = data
    return schema


def _validate_schema(schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(schema, dict):
        return False, ["Schema is not an object"]
    if "meta" not in schema or not isinstance(schema.get("meta"), dict):
        errors.append("Missing/invalid 'meta' object")
    if "data" not in schema or not isinstance(schema.get("data"), list) or not schema["data"]:
        errors.append("Missing/invalid 'data' array with at least one object template")
    else:
        if not isinstance(schema["data"][0], dict):
            errors.append("First element of 'data' must be an object template")
    return len(errors) == 0, errors


class SchemaGenerator:
    def __init__(self):
        # Prefer a dedicated role; falls back to DEFAULT_MODEL if missing.
        self.llm = LLMProvider("schema_generator")

    async def generate(self, url: str, prompt: str) -> dict:
        """
        Pure reasoning-based schema generation. 
        Analyzes the user prompt to design an optimal JSON structure.
        """
        logger.info(f"Generating logical schema for prompt: {prompt}")

        base_instructions = f"""
                        You are a Strategic Data Architect specialized in web scraping.
                        Design a JSON output *shape* (not data) that an extraction agent should fill.

                        TARGET URL: {url}
                        USER PROMPT: {prompt}

                        REQUIREMENTS:
                        - Return ONLY a valid JSON object.
                        - The top-level object MUST contain:
                        - "meta": object (constraints, notes, pagination, counts, source hints)
                        - "data": array with ONE object TEMPLATE as the first element (fields to extract)
                        - Use JSON-friendly placeholder types, not real data:
                        - "string", "number", "boolean", "date", "url"
                        - arrays as ["string"] / ["object"] style examples
                        - nested objects allowed
                        - Prefer snake_case keys.
                        - Include inferred constraints in meta, e.g. count/top_n, sort order, timeframe, currency, units.
                        """

        try:
            last_error: Optional[str] = None
            for attempt in range(1, 4):
                system_prompt = base_instructions
                if last_error:
                    system_prompt += f"\nFIX PREVIOUS ISSUES:\n- {last_error}\n"

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Generate the schema now."},
                ]
                logger.debug(f"SchemaGenerator attempt {attempt} request: {system_prompt}")

                # LLM call is sync; run in thread so FastAPI loop isn't blocked.
                response = await asyncio.to_thread(
                    self.llm.call, messages, {"type": "json_object"}
                )

                if not response:
                    last_error = "LLM returned no response"
                    continue

                raw = response.choices[0].message.content
                try:
                    schema = json.loads(raw)
                except Exception as e:
                    last_error = f"Returned content was not valid JSON: {e}"
                    continue

                schema = _normalize_schema(schema)
                ok, errors = _validate_schema(schema)
                if not ok:
                    last_error = "; ".join(errors)
                    continue

                logger.info("Schema generation successful.")
                logger.debug(f"Generated Schema: {json.dumps(schema, indent=2)}")
                return schema

            logger.error(f"Schema generation failed after retries: {last_error}")
            return {"error": f"Schema generation failed: {last_error or 'unknown error'}"}
        except Exception as e:
            logger.error(f"Schema generation error: {str(e)}")
            return {"error": f"Schema generation error: {str(e)}"}
