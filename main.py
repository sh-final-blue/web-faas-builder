"""FastAPI application for Spin K8s Deployment Tool."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router as api_router

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
