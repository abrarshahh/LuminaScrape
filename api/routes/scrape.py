import uuid
import asyncio
import traceback
from fastapi import APIRouter, HTTPException, BackgroundTasks
from schemas.api_models import (
    SchemaGenerationRequest, SchemaGenerationResponse,
    ScrapeRequest, ScrapeResponse, TaskStatusResponse
)
from agents.schema_generator import SchemaGenerator
from core.orchestrator import app as workflow_app
from core.logger import get_logger

router = APIRouter(prefix="/v1", tags=["scrape"])
logger = get_logger(__name__)

# In-memory storage (Replace with DB later)
sessions_db = {}
tasks_db = {}

@router.post("/generate-schema", response_model=SchemaGenerationResponse)
async def generate_schema(request: SchemaGenerationRequest):
    logger.info(f"API Request: generate-schema for URL: {request.url}")
    try:
        generator = SchemaGenerator()
        schema = await generator.generate(request.url, request.prompt)
        
        session_id = str(uuid.uuid4())
        sessions_db[session_id] = {"url": request.url, "prompt": request.prompt}
        
        logger.info(f"Generated schema for session {session_id}")
        return SchemaGenerationResponse(session_id=session_id, generated_schema=schema)
    except Exception as e:
        logger.error(f"Error in generate_schema: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    logger.info(f"API Request: scrape for session: {request.session_id}")
    
    if request.session_id not in sessions_db:
        logger.warning(f"Session {request.session_id} not found")
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_db[request.session_id]
    task_id = str(uuid.uuid4())
    
    tasks_db[task_id] = {
        "status": "pending",
        "data": None,
        "error": None
    }

    # Prepare initial state
    initial_state = {
        "messages": [],
        "url": session["url"],
        "prompt": session["prompt"],
        "page_metadata": {},
        "extraction_result": None,
        "is_valid": False,
        "feedback": "",
        "step_count": 0,
        "schema": request.generated_schema,
        "task_id": task_id
    }

    background_tasks.add_task(run_scrape_task, task_id, initial_state)
    logger.info(f"Scrape task {task_id} queued in background")
    
    return ScrapeResponse(task_id=task_id)

async def run_scrape_task(task_id: str, initial_state: dict):
    logger.info(f"Starting background task: {task_id}")
    try:
        tasks_db[task_id]["status"] = "running"
        
        # Execute LangGraph workflow
        final_state = await workflow_app.ainvoke(initial_state)
        
        tasks_db[task_id]["status"] = "completed"
        tasks_db[task_id]["data"] = final_state.get("extraction_result")
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        logger.debug(traceback.format_exc())
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = str(e)

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    logger.debug(f"API Request: get-status for task: {task_id}")
    if task_id not in tasks_db:
        logger.warning(f"Task {task_id} not found in DB")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        data=task.get("data"),
        error=task.get("error")
    )
