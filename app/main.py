"""
FastAPI Application Entry Point

This is the main FastAPI application file that replaces the Flask app.
It sets up the FastAPI app with CORS, documentation, and route registration.

Migration Status: Phase 1 - Foundation & HTL
- Establishes FastAPI foundation
- Maintains compatibility with existing Flask API
- Adds automatic OpenAPI documentation generation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import routers 
from app.routers import htl, combustion, fermentation, health, v2_example

# Import middleware
from app.middleware import (
    ErrorHandlerMiddleware, 
    PerformanceMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware
)

# Create FastAPI application
app = FastAPI(
    title="Waste-to-Energy Processing API",
    description="High-performance API for waste-to-energy calculations",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add custom middleware (order matters - last added runs first)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(PerformanceMiddleware, slow_request_threshold=0.5)
app.add_middleware(RateLimitMiddleware, requests_per_minute=30, requests_per_hour=500)
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS (same as Flask-CORS settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers with API v1 prefix (matching Flask structure)
app.include_router(htl.router, prefix="/api/v1", tags=["HTL"])
app.include_router(combustion.router, prefix="/api/v1", tags=["Combustion"])
app.include_router(fermentation.router, prefix="/api/v1", tags=["Fermentation"])

# Register health monitoring endpoints (no API version prefix for standard health endpoints)
app.include_router(health.router, tags=["Health"])

# Register API v2 example endpoints (demonstrates versioning)
app.include_router(v2_example.router, prefix="/api/v2", tags=["API v2"])

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Waste-to-Energy Processing API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "api_versions": {
            "v1": "/api/v1",
            "v2": "/api/v2"
        },
        "endpoints": {
            "htl": "/api/v1/htl/",
            "combustion": "/api/v1/combustion/",
            "fermentation": "/api/v1/fermentation/"
        },
        "monitoring": {
            "health": "/health",
            "readiness": "/ready", 
            "metrics": "/metrics",
            "performance": "/performance"
        }
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# Development server (for uv run)
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )