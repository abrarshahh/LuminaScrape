from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from core.llm import LLMProvider
from core.state import AgentState
from core.logger import get_logger, log_agent_interaction
import json

logger = get_logger(__name__)


def _normalize_next_action(raw: Optional[str], feedback: str) -> str:
    """
    Ensure routing signal is always one of: retry_extract | navigate.
    If model output is weak/invalid, infer from feedback text.
    """
    if raw in {"retry_extract", "navigate"}:
        return raw

    fb = (feedback or "").lower()
    navigate_hints = [
        "wrong page",
        "not on this page",
        "navigate",
        "click",
        "scroll",
        "pagination",
        "multiple pages",
        "list page",
        "detail page",
        "not found on current page",
    ]
    if any(h in fb for h in navigate_hints):
        return "navigate"
    return "retry_extract"

class OverseerAgent:
    def __init__(self):
        self.llm = LLMProvider("overseer")

    async def run(self, state: AgentState):
        """
        Validates the extraction result against the prompt and schema.
        """
        prompt = state["prompt"]
        result = state.get("extraction_result")
        schema = state.get("schema")
        task_id = state.get("task_id", "UNKNOWN")
        step_count = state.get("step_count", 0)
        page_metadata = state.get("page_metadata") or {}
        navigation = state.get("navigation") or {}
        extraction_validation_errors = state.get("extraction_validation_errors") or []
        
        logger.info(f"[{task_id}] Overseer: Validating extraction (Attempt {step_count + 1})")
        
        if not result:
            logger.warning(f"[{task_id}] Overseer: No data found to validate")
            return {
                "is_valid": False,
                "feedback": "No data was extracted.",
                "next_action": "navigate",
                "messages": [{"role": "system", "content": "Overseer: No data extracted to validate."}]
            }

        # If extractor itself reports schema/type errors, prefer a cheap deterministic route:
        # invalid + retry_extract (unless page is clearly marked not-ready by navigator).
        if extraction_validation_errors:
            nav_status = str((navigation or {}).get("status", "")).lower()
            next_action = "navigate" if nav_status in {"stopped", "failed"} else "retry_extract"
            feedback = "Extractor output has schema/type validation issues: " + "; ".join(
                [str(e) for e in extraction_validation_errors[:10]]
            )
            return {
                "is_valid": False,
                "feedback": feedback,
                "next_action": next_action,
                "step_count": step_count + 1,
                "messages": [{"role": "assistant", "content": f"Overseer Decision: Invalid - {feedback}"}],
            }

        # 1. Construct Validation Prompt
        system_prompt = f"""
        You are a Quality Control agent for a web scraper.
        Your goal is to verify if the extracted data accurately answers the user's prompt.
        
        USER PROMPT: {prompt}
        TARGET SCHEMA (if provided): {json.dumps(schema) if schema else "null"}
        PAGE METADATA: {json.dumps(page_metadata)[:3000]}
        NAVIGATION STATUS: {json.dumps(navigation)[:3000]}
        EXTRACTED DATA: {json.dumps(result)}
        
        Return ONLY JSON in one of these formats:
        - If correct: {{"valid": true}}
        - If incorrect/incomplete: {{"valid": false, "reason": "...", "next_action": "retry_extract" | "navigate"}}

        Guidance for next_action:
        - Use "navigate" if the current page likely is NOT the right page (wrong section),
          or the requested data is probably on multiple pages / detail pages / requires scrolling or clicking.
        - Use "retry_extract" if the data is on the page but formatting/field mapping/types are wrong.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Validate the extraction result."}
        ]

        # 2. Call LLM
        logger.debug(f"[{task_id}] Overseer: Calling LLM for validation")
        response = await asyncio.to_thread(self.llm.call, messages, {"type": "json_object"})
        
        if not response:
            logger.error(f"[{task_id}] Overseer: LLM failed to respond")
            return {"is_valid": False, "feedback": "Validation failed: LLM unresponsive.", "next_action": "retry_extract"}

        try:
            validation = json.loads(response.choices[0].message.content)
            is_valid = validation.get("valid", False)
            feedback = validation.get("reason", "Success")
            next_action_raw = validation.get("next_action") or ("retry_extract" if not is_valid else None)
            next_action = _normalize_next_action(next_action_raw, feedback) if not is_valid else None
            new_step_count = step_count + 1
            
            logger.info(f"[{task_id}] Overseer: Validation result - {'VALID' if is_valid else 'INVALID'}")
            
            # Log to agents.log
            log_agent_interaction(
                "Overseer", 
                task_id, 
                f"Validation for: {prompt}", 
                f"RESULT: {'VALID' if is_valid else 'INVALID'}\nREASON: {feedback}\nNEXT_ACTION: {next_action}",
                is_final=is_valid
            )
            
            return {
                "is_valid": is_valid,
                "feedback": feedback,
                "next_action": next_action,
                "step_count": new_step_count,
                "messages": [{"role": "assistant", "content": f"Overseer Decision: {'Valid' if is_valid else 'Invalid - ' + feedback}"}]
            }
        except Exception as e:
            logger.error(f"[{task_id}] Overseer: Failed to parse validation response: {e}")
            return {"is_valid": False, "feedback": f"Validation parsing error: {e}", "next_action": "retry_extract"}
