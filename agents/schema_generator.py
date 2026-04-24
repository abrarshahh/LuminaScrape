import json
from core.llm import LLMProvider

class SchemaGenerator:
    def __init__(self):
        # Using overseer for high-quality reasoning
        self.llm = LLMProvider("overseer") 

    async def generate(self, url: str, prompt: str) -> dict:
        """
        Pure reasoning-based schema generation. 
        Analyzes the user prompt to design an optimal JSON structure.
        """
        system_prompt = f"""
        You are a Strategic Data Architect specialized in web scraping.
        Your goal is to design a JSON schema based on a user's natural language prompt.
        
        TARGET URL: {url}
        USER PROMPT: {prompt}
        
        THINKING PROCESS:
        1. Identify the core entities requested (e.g., movies, products, articles).
        2. Extract specific fields mentioned (e.g., "title", "IMDB rating", "price").
        3. Identify structural constraints (e.g., "10 items", "sorted by date").
        4. Design a clean, hierarchical JSON structure that handles these requirements.
        
        OUTPUT RULES:
        - Return ONLY a valid JSON object representing the suggested schema.
        - Use descriptive keys.
        - Include a "meta" field if the prompt contains constraints like "limit" or "count".
        
        EXAMPLE OUTPUT:
        {{
          "meta": {{ "limit": 10, "category": "Action" }},
          "data": [
            {{ "name": "string", "rating": "number", "release_year": "number" }}
          ]
        }}
        """
        
        try:
            messages = [{"role": "system", "content": system_prompt}]
            response = self.llm.call(messages, response_format={"type": "json_object"})
            
            if response:
                return json.loads(response.choices[0].message.content)
            return {"error": "LLM failed to generate schema"}
        except Exception as e:
            return {"error": f"Schema generation error: {str(e)}"}
