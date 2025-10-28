from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys

from app.config import settings
from app.database import init_db, engine
from app.middleware.security import setup_security_middleware
from app.routes import plaid, transactions, webhooks, health
from app.utils.logger import setup_logging
from app.routes import ai  # Add this line

# Setup logging
setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting FinHealth360 Backend")
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)
    
    yield
    
    # Shutdown
    await engine.dispose()
    logger.info("🛑 FinHealth360 Backend shut down")

app = FastAPI(
    title=settings.APP_NAME,
    description="Secure Financial + Health Wellness Platform Backend",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# Setup middleware
setup_security_middleware(app)

# Include routers
app.include_router(plaid.router)
app.include_router(transactions.router)
app.include_router(webhooks.router)
app.include_router(health.router)

@app.get("/")
async def root():
    return {
        "message": "🏥 FinHealth360 Backend API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "healthy"
    }

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found"}
    )
app.include_router(ai.router)  # Add this line

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
        ssl_keyfile="localhost-key.pem" if settings.ENVIRONMENT == "production" else None,
        ssl_certfile="localhost.pem" if settings.ENVIRONMENT == "production" else None
    )
