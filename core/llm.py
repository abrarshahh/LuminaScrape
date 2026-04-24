import os
import yaml
import litellm
from dotenv import load_dotenv

load_dotenv()

class LLMProvider:
    def __init__(self, agent_name=None):
        self.config = self._load_config()
        self.agent_name = agent_name
        self.model_info = self._get_model_info(agent_name)
        self.model_name = self.model_info.get("model", "gpt-4o-mini")
        self.temperature = self.model_info.get("temperature", 0.0)

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.yaml")
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading models.yaml: {e}")
            return {"agents": {}}

    def _get_model_info(self, agent_name):
        if not agent_name:
            return {"model": os.getenv("DEFAULT_MODEL", "gpt-4o-mini")}
        return self.config.get("agents", {}).get(agent_name, {})

    def call(self, messages, tools=None, response_format=None):
        """
        Generic wrapper for LLM calls using LiteLLM.
        """
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
        }
        
        if tools:
            kwargs["tools"] = tools
            
        if response_format:
            kwargs["response_format"] = response_format
            
        try:
            response = litellm.completion(**kwargs)
            return response
        except Exception as e:
            print(f"Error calling LLM ({self.model_name}): {e}")
            return None

# Usage:
# pilot_llm = LLMProvider("pilot")
# response = pilot_llm.call([{"role": "user", "content": "Analyze screenshot"}])
