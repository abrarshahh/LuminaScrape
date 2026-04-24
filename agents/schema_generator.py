import json
from core.llm import LLMProvider
from core.logger import get_logger

logger = get_logger(__name__)

class SchemaGenerator:
    def __init__(self):
        self.llm = LLMProvider("overseer") 

    async def generate(self, url: str, prompt: str) -> dict:
        """
        Pure reasoning-based schema generation. 
        Analyzes the user prompt to design an optimal JSON structure.
        """
        logger.info(f"Generating logical schema for prompt: {prompt}")
        
        system_prompt = f"""
        You are a Strategic Data Architect specialized in web scraping.
        Your goal is to design a JSON schema based on a user's natural language prompt.
        
        TARGET URL: {url}
        USER PROMPT: {prompt}
        
        THINKING PROCESS:
        1. Identify the core entities requested.
        2. Extract specific fields mentioned.
        3. Identify structural constraints.
        4. Design a clean, hierarchical JSON structure.
        
        OUTPUT RULES:
        - Return ONLY a valid JSON object representing the suggested schema.
        - Include a "meta" field for constraints.
        """
        
        try:
            messages = [{"role": "system", "content": system_prompt}]
            logger.debug(f"SchemaGenerator Request: {system_prompt}")
            
            response = self.llm.call(messages, response_format={"type": "json_object"})
            
            if response:
                schema = json.loads(response.choices[0].message.content)
                logger.info("Schema generation successful.")
                logger.debug(f"Generated Schema: {json.dumps(schema, indent=2)}")
                return schema
                
            logger.error("LLM failed to return a schema response.")
            return {"error": "LLM failed to generate schema"}
        except Exception as e:
            logger.error(f"Schema generation error: {str(e)}")
            return {"error": f"Schema generation error: {str(e)}"}
