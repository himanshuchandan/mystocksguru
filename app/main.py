from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from loguru import logger
from pathlib import Path

from app.config import settings
from app.scheduler import start_scheduler, stop_scheduler
from app.routers import alerts, portfolio, analysis, shadow_portfolio


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Market Copilot starting...")
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Market Copilot stopped.")


app = FastAPI(
    title="AI Market Copilot",
    description="AI-powered Indian stock market research assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(shadow_portfolio.router, prefix="/api/shadow", tags=["Shadow Portfolio"])


@app.get("/health")
async def health():
    return {"status": "ok", "llm_provider": settings.llm_provider, "dashboard_enabled": settings.enable_dashboard}


@app.get("/")
async def dashboard():
    """Serve the dashboard UI."""
    return FileResponse(Path(__file__).parent / "templates" / "index.html")
