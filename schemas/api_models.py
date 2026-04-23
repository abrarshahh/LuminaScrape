from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ScrapeRequest(BaseModel):
    url: str = Field(..., description="The target URL to start scraping from.")
    prompt: str = Field(..., description="Natural language instructions for the agent.")
    schema_id: Optional[str] = Field(None, description="Optional ID for a predefined extraction schema.")
    max_steps: int = Field(10, description="Maximum number of steps the agent can take.")
    model_overrides: Optional[Dict[str, str]] = Field(None, description="Override models for specific agents.")

class ScrapeResponse(BaseModel):
    task_id: str
    status: str = "pending"

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    data: Optional[Any] = None
    error: Optional[str] = None
    steps_taken: int = 0
    logs: List[str] = []

class ConfigUpdateRequest(BaseModel):
    agents: Optional[Dict[str, Any]] = None
    global_settings: Optional[Dict[str, Any]] = None
