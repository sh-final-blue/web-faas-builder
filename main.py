"""FastAPI application for Spin K8s Deployment Tool."""

import logging
import os
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router as api_router

# Configure logging level from environment variable
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, LOG_LEVEL, logging.INFO)

# Configure root logger
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)

# Set uvicorn loggers to same level
logging.getLogger("uvicorn").setLevel(log_level)
logging.getLogger("uvicorn.access").setLevel(log_level)
logging.getLogger("uvicorn.error").setLevel(log_level)

logger = logging.getLogger(__name__)
logger.info(f"Log level set to: {LOG_LEVEL}")


# Filter out health check logs from uvicorn access logs
class HealthCheckFilter(logging.Filter):
    """Filter to exclude health check endpoint logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False for health check requests to exclude them from logs."""
        return "/health" not in record.getMessage()

app = FastAPI(
    title="Spin K8s Deployment Tool",
    description="FastAPI-based API server for building, pushing, and deploying Spin applications to Kubernetes",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for internal server errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


# Mount API router
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    # Apply health check filter to uvicorn access logger
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
