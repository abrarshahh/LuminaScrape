import sys
import asyncio
import logging

# CRITICAL: Windows asyncio fix must be applied BEFORE any other imports
if sys.platform == "win32":
    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import scrape, config
from core.ollama_manager import OllamaManager
from core.logger import setup_logging

# Initialize Logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Ollama Manager
ollama = OllamaManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    ollama.start()
    yield
    logger.info("Application shutting down...")
    ollama.stop()

app = FastAPI(
    title="LuminaScrape API",
    description="Autonomous Multi-Agent Browser Scraping System",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(scrape.router, prefix="/api")
app.include_router(config.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to LuminaScrape API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server directly...")
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="proactor")
