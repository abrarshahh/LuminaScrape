from core.llm import LLMProvider
from core.state import AgentState
import json

class OverseerAgent:
    def __init__(self):
        self.llm = LLMProvider("overseer")

    async def run(self, state: AgentState):
        """
        Validates the extraction result against the prompt and schema.
        """
        prompt = state["prompt"]
        result = state.get("extraction_result")
        
        if not result:
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
        print("[Overseer] Validating extraction result...")
        response = self.llm.call(messages, response_format={"type": "json_object"})
        
        if not response:
            return {"is_valid": False, "feedback": "Validation failed: LLM unresponsive."}

        try:
            validation = json.loads(response.choices[0].message.content)
            is_valid = validation.get("valid", False)
            feedback = validation.get("reason", "Success")
            
            new_step_count = state.get("step_count", 0) + 1
            
            return {
                "is_valid": is_valid,
                "feedback": feedback,
                "step_count": new_step_count,
                "messages": [{"role": "assistant", "content": f"Overseer Decision: {'Valid' if is_valid else 'Invalid - ' + feedback}"}]
            }
        except Exception as e:
            return {"is_valid": False, "feedback": f"Validation parsing error: {e}"}
