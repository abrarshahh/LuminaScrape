from fastapi import APIRouter
from schemas.settings import load_system_config

router = APIRouter(prefix="/v1/config", tags=["Configuration"])

@router.get("/")
async def get_config():
    config = load_system_config()
    return config.model_dump()
