from core.llm import LLMProvider
from core.state import AgentState
from core.logger import get_logger, log_agent_interaction
import json

logger = get_logger(__name__)

class OverseerAgent:
    def __init__(self):
        self.llm = LLMProvider("overseer")

    async def run(self, state: AgentState):
        """
        Validates the extraction result against the prompt and schema.
        """
        prompt = state["prompt"]
        result = state.get("extraction_result")
        task_id = state.get("task_id", "UNKNOWN")
        step_count = state.get("step_count", 0)
        
        logger.info(f"[{task_id}] Overseer: Validating extraction (Attempt {step_count + 1})")
        
        if not result:
            logger.warning(f"[{task_id}] Overseer: No data found to validate")
            return {
                "is_valid": False,
                "feedback": "No data was extracted.",
                "messages": [{"role": "system", "content": "Overseer: No data extracted to validate."}]
            }

        # 1. Construct Validation Prompt
        system_prompt = f"""
        You are a Quality Control agent for a web scraper.
        Your goal is to verify if the extracted data accurately answers the user's prompt.
        
        USER PROMPT: {prompt}
        EXTRACTED DATA: {json.dumps(result)}
        
        If the data is correct and answers the prompt, return: {{"valid": true}}
        If the data is missing, incorrect, or incomplete, return: {{"valid": false, "reason": "Detailed explanation of what is missing or wrong"}}
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Validate the extraction result."}
        ]

        # 2. Call LLM
        logger.debug(f"[{task_id}] Overseer: Calling LLM for validation")
        response = self.llm.call(messages, response_format={"type": "json_object"})
        
        if not response:
            logger.error(f"[{task_id}] Overseer: LLM failed to respond")
            return {"is_valid": False, "feedback": "Validation failed: LLM unresponsive."}

        try:
            validation = json.loads(response.choices[0].message.content)
            is_valid = validation.get("valid", False)
            feedback = validation.get("reason", "Success")
            new_step_count = step_count + 1
            
            logger.info(f"[{task_id}] Overseer: Validation result - {'VALID' if is_valid else 'INVALID'}")
            
            # Log to agents.log
            log_agent_interaction(
                "Overseer", 
                task_id, 
                f"Validation for: {prompt}", 
                f"RESULT: {'VALID' if is_valid else 'INVALID'}\nREASON: {feedback}",
                is_final=is_valid
            )
            
            return {
                "is_valid": is_valid,
                "feedback": feedback,
                "step_count": new_step_count,
                "messages": [{"role": "assistant", "content": f"Overseer Decision: {'Valid' if is_valid else 'Invalid - ' + feedback}"}]
            }
        except Exception as e:
            logger.error(f"[{task_id}] Overseer: Failed to parse validation response: {e}")
            return {"is_valid": False, "feedback": f"Validation parsing error: {e}"}
