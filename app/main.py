"""
FastAPI Application Entry Point (local-dev / "everything" entrypoint).

Registers all six routers (three light lookup + three heavy calc + health)
in a single app, for local development (`uv run uvicorn app.main:app`) and
for the test suite's TestClient. Lambda deployments use the four separate
entrypoints in app/entrypoints/ instead — see guides/lambda-restructure-design.md.
"""

import uvicorn

from app.app_factory import create_app, ALLOWED_ORIGINS  # noqa: F401 (ALLOWED_ORIGINS re-exported for tests/test_cors.py)
from app.routers import (
    health,
    htl_lookup, htl_calc,
    combustion_lookup, combustion_calc,
    fermentation_lookup, fermentation_calc,
)

app = create_app()

app.include_router(htl_calc.router, prefix="/api/v1", tags=["HTL"])
app.include_router(htl_lookup.router, prefix="/api/v1", tags=["HTL"])
app.include_router(combustion_calc.router, prefix="/api/v1", tags=["Combustion"])
app.include_router(combustion_lookup.router, prefix="/api/v1", tags=["Combustion"])
app.include_router(fermentation_calc.router, prefix="/api/v1", tags=["Fermentation"])
app.include_router(fermentation_lookup.router, prefix="/api/v1", tags=["Fermentation"])
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


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )