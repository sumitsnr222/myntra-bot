"""
Myntra Web Suite — Entry point
Starts the FastAPI web server.
"""
import asyncio
import logging
import uvicorn

from contextlib import asynccontextmanager
from backend.api import app, load_accounts, save_accounts
from backend.browser import shutdown

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Lifecycle ────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application):
    """Startup/shutdown hooks."""
    logger.info("🚀 Starting Myntra Web Suite v4...")
    await load_accounts()
    logger.info(f"🌐 Dashboard ready at http://localhost:8000")
    yield
    await save_accounts()
    await shutdown()
    logger.info("👋 Shutting down.")

app.router.lifespan_context = lifespan

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
