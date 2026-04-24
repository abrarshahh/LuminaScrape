import os
import yaml
import litellm
from dotenv import load_dotenv
from core.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

class LLMProvider:
    def __init__(self, agent_role: str):
        self.role = agent_role
        self.config = self._load_config()
        self.model_name = self.config['model']
        self.temperature = self.config.get('temperature', 0.0)
        logger.debug(f"Initialized LLMProvider for role: {agent_role} using model: {self.model_name}")

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.yaml")
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config['agents'][self.role]
        except Exception as e:
            logger.error(f"Failed to load LLM configuration for {self.role}: {e}")
            # Fallback to a safe default if config fails
            return {"model": os.getenv("DEFAULT_MODEL", "gpt-4o-mini"), "temperature": 0.0}

    def call(self, messages, response_format=None):
        """
        Main entry point for LLM calls. Handles retries and logging.
        """
        logger.info(f"Calling LLM ({self.model_name}) for role: {self.role}")
        try:
            # LiteLLM handles multiple providers (Ollama, OpenAI, Anthropic, etc.)
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
            }
            
            if response_format:
                kwargs["response_format"] = response_format

            logger.debug(f"LLM Request Payload: {messages}")
            
            response = litellm.completion(**kwargs)
            
            # Log token usage if available
            usage = getattr(response, 'usage', None)
            if usage:
                logger.debug(f"LLM Usage: Prompt={usage.prompt_tokens}, Completion={usage.completion_tokens}, Total={usage.total_tokens}")
            
            return response
            
        except Exception as e:
            logger.error(f"LLM Call failed for {self.role} ({self.model_name}): {e}")
            
            # Fallback logic if enabled
            if os.getenv("ENABLE_FALLBACKS") == "true":
                fallback_model = os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
                logger.warning(f"Attempting fallback to {fallback_model}...")
                try:
                    return litellm.completion(model=fallback_model, messages=messages)
                except Exception as fe:
                    logger.error(f"Fallback also failed: {fe}")
            
            return None
