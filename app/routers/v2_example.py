"""
API Version 2 Example Router

This demonstrates how to implement API versioning in FastAPI.
Future API versions can follow this pattern.

This is a placeholder showing how v2 endpoints could be structured
with potential improvements like:
- Different response formats
- Enhanced features
- Breaking changes
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Dict, Any

# Create v2 router
router = APIRouter()


class V2HealthResponse(BaseModel):
    """Enhanced health response for API v2"""
    api_version: str
    status: str
    timestamp: float
    system_info: Dict[str, Any]


@router.get(
    "/health",
    response_model=V2HealthResponse,
    summary="Health check (API v2)",
    description="Enhanced health check with additional system information",
    tags=["Health v2"]
)
async def health_check_v2():
    """
    API v2 health check with enhanced response format.
    
    This demonstrates how API versioning can provide:
    - Enhanced response formats
    - Additional data
    - Backward compatibility
    """
    import time
    import psutil
    
    return V2HealthResponse(
        api_version="2.0",
        status="healthy",
        timestamp=time.time(),
        system_info={
            "memory_mb": psutil.virtual_memory().used / 1024 / 1024,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "process_count": len(psutil.pids())
        }
    )


@router.get(
    "/info",
    summary="API information (v2)",
    description="Comprehensive API information for version 2",
    tags=["Info v2"]
)
async def api_info_v2():
    """
    Enhanced API information endpoint for v2.
    """
    return {
        "api_version": "2.0",
        "features": [
            "Enhanced error handling",
            "Performance monitoring", 
            "Rate limiting",
            "Security headers",
            "Comprehensive health checks"
        ],
        "breaking_changes": [
            "Enhanced response formats",
            "Additional validation",
            "Improved error messages"
        ],
        "deprecated_in_v1": [],
        "endpoints": {
            "htl": "/api/v2/htl/",
            "combustion": "/api/v2/combustion/",
            "fermentation": "/api/v2/fermentation/",
            "health": "/api/v2/health",
            "metrics": "/api/v2/metrics"
        }
    }