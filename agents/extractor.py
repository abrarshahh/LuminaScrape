import json
from core.llm import LLMProvider
from tools.crawl_page import crawl_page
from tools.take_screenshot import take_screenshot
from tools.get_accessibility_tree import get_accessibility_tree
from tools.click_element import click_element
from tools.scroll_page import scroll_page
from core.state import AgentState

class ExtractorAgent:
    def __init__(self):
        self.llm = LLMProvider("extractor")

    async def run(self, state: AgentState, page):
        """
        Extracts the requested data from the prepared page.
        """
        prompt = state["prompt"]
        schema = state.get("schema")
        
        # 1. Gather context
        print("[Extractor] Gathering page context...")
        ax_tree = await get_accessibility_tree(page)
        markdown = await crawl_page(page)
        
        # 2. Construct LLM Prompt
        system_prompt = f"""
        You are an expert data extraction agent. 
        Your goal is to extract structured data from the provided webpage context based on the user's prompt.
        
        USER PROMPT: {prompt}
        SCHEMA: {json.dumps(schema) if schema else "None provided. Return structured JSON."}
        
        CONTEXT (AXTree):
        {json.dumps(ax_tree.get('accessibility_tree'))[:5000]}
        
        CONTEXT (Markdown):
        {markdown.get('markdown')[:5000] if markdown.get('markdown') else "N/A"}
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Extract the data into a valid JSON object."}
        ]

        # 3. Call LLM
        print("[Extractor] Calling LLM for data extraction...")
        response = self.llm.call(messages, response_format={"type": "json_object"})
        
        if not response:
            return {"messages": [{"role": "system", "content": "Extraction failed: LLM returned no response."}]}

        try:
            extracted_data = json.loads(response.choices[0].message.content)
            return {
                "extraction_result": extracted_data,
                "messages": [{"role": "assistant", "content": f"Extracted: {json.dumps(extracted_data)[:200]}..."}]
            }
        except Exception as e:
            return {"messages": [{"role": "system", "content": f"Failed to parse extraction result: {e}"}]}
