import yaml
import os
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from core.logger import get_logger

router = APIRouter(prefix="/v1/config", tags=["config"])
logger = get_logger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "models.yaml")

@router.get("/")
async def get_config():
    logger.debug("API Request: get-config")
    try:
        if not os.path.exists(CONFIG_PATH):
            logger.error(f"Config file not found at {CONFIG_PATH}")
            raise HTTPException(status_code=404, detail="Config file not found")
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to read config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-model")
async def update_model(agent: str, model: str):
    logger.info(f"API Request: update-model for agent '{agent}' to '{model}'")
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        if agent not in config["agents"]:
            logger.warning(f"Attempted to update non-existent agent: {agent}")
            raise HTTPException(status_code=404, detail="Agent not found")
            
        config["agents"][agent]["model"] = model
        
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(config, f)
            
        logger.info(f"Model updated successfully for {agent}")
        return {"status": "success", "agent": agent, "new_model": model}
    except Exception as e:
        logger.error(f"Failed to update model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
