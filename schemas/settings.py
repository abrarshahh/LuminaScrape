import os
import yaml
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class AgentConfig(BaseModel):
    model: str
    temperature: float = 0.0
    description: Optional[str] = None

class GlobalSettings(BaseModel):
    fallback_model: str = "gpt-4o-mini"
    enable_fallbacks: bool = False

class SystemConfig(BaseModel):
    agents: Dict[str, AgentConfig]
    global_settings: GlobalSettings

def load_system_config() -> SystemConfig:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.yaml")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    return SystemConfig(**data)

def save_system_config(config: SystemConfig):
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config.model_dump(), f)
