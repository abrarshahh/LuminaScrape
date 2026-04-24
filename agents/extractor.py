from core.llm import LLMProvider
from core.state import AgentState
from tools.get_accessibility_tree import get_accessibility_tree
from tools.crawl_page import crawl_page
from core.logger import get_logger, log_agent_interaction
import json

logger = get_logger(__name__)

class ExtractorAgent:
    def __init__(self):
        self.llm = LLMProvider("extractor")

    async def run(self, state: AgentState, page):
        """
        Extracts structured data from the page markdown and AXTree.
        """
        prompt = state["prompt"]
        schema = state.get("schema")
        task_id = state.get("task_id", "UNKNOWN")
        
        logger.info(f"[{task_id}] Extractor: Starting extraction for prompt: {prompt}")

        # 1. Get Page Context
        logger.debug(f"[{task_id}] Extractor: Gathering page context (Markdown + AXTree)")
        crawl_result = await crawl_page(page)
        markdown = crawl_result.get("markdown", "")
        
        ax_tree = await get_accessibility_tree(page)
        
        # 2. Build LLM Prompt
        system_prompt = f"""
        You are an expert Data Extraction Agent. 
        Analyze the following webpage content (Markdown) and structural data (AXTree).
        Extract the information requested by the user.
        
        USER PROMPT: {prompt}
        
        CONTEXT (AXTree Snapshot):
        {json.dumps(ax_tree.get('accessibility_tree'))[:2000]}
        
        CONTENT (Markdown):
        {markdown[:10000]}
        
        Return ONLY a valid JSON object.
        """
        
        if schema:
            system_prompt += f"\nSTRICT SCHEMA TO FOLLOW:\n{json.dumps(schema)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Extract the data now."}
        ]

        # 3. Call LLM
        logger.debug(f"[{task_id}] Extractor: Calling LLM ({self.llm.model_name})")
        response = self.llm.call(messages, response_format={"type": "json_object"})
        
        if not response:
            logger.error(f"[{task_id}] Extractor: LLM failed to return a response")
            return {"messages": [{"role": "system", "content": "Extractor: LLM failed to respond."}]}

        try:
            extracted_data = json.loads(response.choices[0].message.content)
            logger.info(f"[{task_id}] Extractor: Successfully extracted data")
            
            # Log to agents.log
            log_agent_interaction("Extractor", task_id, prompt, json.dumps(extracted_data, indent=2))
            
            return {
                "extraction_result": extracted_data,
                "messages": [{"role": "assistant", "content": "Data extracted successfully."}]
            }
        except Exception as e:
            logger.error(f"[{task_id}] Extractor: Failed to parse LLM response: {e}")
            return {"messages": [{"role": "system", "content": f"Extractor: Parsing error: {e}"}]}
