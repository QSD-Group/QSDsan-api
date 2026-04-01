"""
FastAPI Application Entry Point

This is the main FastAPI application file that replaces the Flask app.
It sets up the FastAPI app with CORS, documentation, and route registration.

Migration Status: Phase 1 - Foundation & HTL
- Establishes FastAPI foundation
- Maintains compatibility with existing Flask API
- Adds automatic OpenAPI documentation generation
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

# Import routers 
from app.routers import htl, combustion, fermentation, health

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

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Waste-to-Energy Processing API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "api_version": "v1",
        "base_url": "/api/v1",
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
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        field = error["loc"][-1] if error["loc"] else "field"
        input_val = error.get("input", "")
        error_type = error.get("type", "")

        if error_type == "missing":
            messages.append(f"Missing required parameter: '{field}'")
        elif error_type == "enum":
            expected = error.get("ctx", {}).get("expected", "")
            messages.append(f"Invalid {field} '{input_val}'. Valid options: {expected}")
        elif error_type in ("greater_than", "greater_than_equal"):
            messages.append(f"'{field}' must be a positive number (got {input_val})")
        elif error_type in ("float_parsing", "int_parsing"):
            messages.append(f"'{field}' must be a number (got '{input_val}')")
        else:
            messages.append(f"Invalid '{field}': {error.get('msg', error_type)}")

    return JSONResponse(
        status_code=422,
        content={"error": messages[0] if len(messages) == 1 else messages}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
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