from fastapi import APIRouter, HTTPException
import uuid
import asyncio
import traceback
from typing import Dict, Any
from schemas.api_models import (
    SchemaGenerationRequest, 
    SchemaGenerationResponse, 
    ScrapeRequest, 
    ScrapeResponse, 
    TaskStatusResponse
)
from agents.schema_generator import SchemaGenerator
from core.orchestrator import app as workflow_app

router = APIRouter(prefix="/v1", tags=["Scraping"])

# In-memory storage
sessions_db: Dict[str, Dict[str, Any]] = {}
tasks_db: Dict[str, Dict[str, Any]] = {}

@router.post("/generate-schema", response_model=SchemaGenerationResponse)
async def generate_schema(request: SchemaGenerationRequest):
    try:
        print(f"[API] Generating schema for {request.url}...")
        generator = SchemaGenerator()
        schema = await generator.generate(request.url, request.prompt)
        
        session_id = str(uuid.uuid4())
        sessions_db[session_id] = {"url": request.url, "prompt": request.prompt}
        
        return SchemaGenerationResponse(session_id=session_id, generated_schema=schema)
    except Exception as e:
        print(f"[API ERROR] Error in generate_schema: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

async def run_scrape_task(task_id: str, url: str, prompt: str, schema: Dict[str, Any]):
    initial_state = {
        "messages": [{"role": "user", "content": prompt}],
        "url": url,
        "prompt": prompt,
        "page_metadata": {},
        "extraction_result": None,
        "is_valid": False,
        "feedback": "",
        "step_count": 0,
        "schema": schema
    }
    try:
        tasks_db[task_id]["status"] = "running"
        final_state = await workflow_app.ainvoke(initial_state)
        tasks_db[task_id]["status"] = "completed"
        tasks_db[task_id]["data"] = final_state.get("extraction_result")
        tasks_db[task_id]["logs"] = [m["content"] for m in final_state.get("messages", [])]
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = str(e)
        print(f"[API ERROR] Task {task_id} failed: {e}")
        traceback.print_exc()

@router.post("/scrape", response_model=ScrapeResponse)
async def start_scrape(request: ScrapeRequest):
    session = sessions_db.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {"status": "pending", "data": None, "error": None, "logs": []}
    asyncio.create_task(run_scrape_task(task_id, session["url"], session["prompt"], request.generated_schema))
    return ScrapeResponse(task_id=task_id, status="pending")

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks_db[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        data=task.get("data"),
        error=task.get("error")
    )
