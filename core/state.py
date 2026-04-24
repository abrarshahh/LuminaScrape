from typing import List, Dict, Any, TypedDict, Annotated, Optional
import operator
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    # The list of messages in the conversation
    messages: Annotated[List[Dict[str, str]], operator.add]
    
    # Target URL
    url: str
    
    # User's extraction goal/prompt
    prompt: str
    
    # Current page metadata
    page_metadata: Dict[str, Any]
    
    # Extraction results
    extraction_result: Optional[Dict[str, Any]]
    
    # Validation status and feedback
    is_valid: bool
    feedback: str
    
    # Steps taken to prevent infinite loops
    step_count: int
    
    # Predefined extraction schema (optional)
    schema: Optional[Dict[str, Any]]

    # Tracking Task ID for logging
    task_id: Optional[str]
