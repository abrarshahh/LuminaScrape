from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SchemaGenerationRequest(BaseModel):
    url: str = Field(..., description="The target URL to analyze.")
    prompt: str = Field(..., description="What data you want to extract.")

class SchemaGenerationResponse(BaseModel):
    session_id: str
    generated_schema: Dict[str, Any]

class ScrapeRequest(BaseModel):
    session_id: str = Field(..., description="The session ID from the schema generation step.")
    generated_schema: Dict[str, Any] = Field(..., description="The (possibly modified) JSON structure to use.")

class ScrapeResponse(BaseModel):
    task_id: str
    status: str = "pending"

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    data: Optional[Any] = None
    error: Optional[str] = None
