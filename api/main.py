import sys
import asyncio

# CRITICAL: Windows asyncio fix must be applied BEFORE any other imports
if sys.platform == "win32":
    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import scrape, config
from core.ollama_manager import OllamaManager

# Initialize Ollama Manager
ollama = OllamaManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure Ollama starts
    ollama.start()
    yield
    # Stop Ollama on shutdown
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
    # When running directly, ensure we use the correct loop
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="proactor")
