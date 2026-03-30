"""
Health Check FastAPI Router

This router provides health monitoring endpoints for the application.
These are essential for production deployments, monitoring, and load balancers.

Endpoints:
- GET /health - Basic health check
- GET /ready - Readiness check (includes dependency verification)
- GET /metrics - Basic application metrics
"""

import time
import psutil
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any
import os

# Create router
router = APIRouter()

# Store application start time
app_start_time = time.time()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str
    timestamp: float
    uptime_seconds: float


class ReadinessResponse(BaseModel):
    """Readiness check response model"""
    status: str
    version: str
    timestamp: float
    uptime_seconds: float
    dependencies: Dict[str, str]
    system: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Basic metrics response model"""
    uptime_seconds: float
    memory_usage_mb: float
    cpu_percent: float
    disk_usage_percent: float
    python_version: str
    process_id: int


def check_dependencies() -> Dict[str, str]:
    """Check if critical dependencies are available"""
    dependencies = {}
    
    try:
        import pandas
        dependencies["pandas"] = "OK"
    except ImportError:
        dependencies["pandas"] = "FAILED"
    
    try:
        import numpy
        dependencies["numpy"] = "OK"
    except ImportError:
        dependencies["numpy"] = "FAILED"
    
    try:
        import biosteam
        dependencies["biosteam"] = "OK"
    except ImportError:
        dependencies["biosteam"] = "FAILED"
    
    try:
        from app.services import htl_service
        dependencies["htl_service"] = "OK"
    except ImportError:
        dependencies["htl_service"] = "FAILED"
    
    try:
        from app.services import combustion_service
        dependencies["combustion_service"] = "OK"
    except ImportError:
        dependencies["combustion_service"] = "FAILED"
    
    try:
        from app.services import fermentation_service
        dependencies["fermentation_service"] = "OK"
    except ImportError:
        dependencies["fermentation_service"] = "FAILED"
    
    # Check data files
    try:
        htl_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "htl", "htl_data.csv")
        if os.path.exists(htl_data_path):
            dependencies["htl_data"] = "OK"
        else:
            dependencies["htl_data"] = "MISSING"
    except Exception:
        dependencies["htl_data"] = "ERROR"
    
    try:
        combustion_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "combustion", "combustion_data.csv")
        if os.path.exists(combustion_data_path):
            dependencies["combustion_data"] = "OK"
        else:
            dependencies["combustion_data"] = "MISSING"
    except Exception:
        dependencies["combustion_data"] = "ERROR"
    
    try:
        fermentation_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "fermentation", "fermentation_data.csv")
        if os.path.exists(fermentation_data_path):
            dependencies["fermentation_data"] = "OK"
        else:
            dependencies["fermentation_data"] = "MISSING"
    except Exception:
        dependencies["fermentation_data"] = "ERROR"
    
    return dependencies


def get_system_info() -> Dict[str, Any]:
    """Get basic system information"""
    try:
        return {
            "memory_usage_mb": psutil.virtual_memory().used / 1024 / 1024,
            "memory_available_mb": psutil.virtual_memory().available / 1024 / 1024,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "disk_usage_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else "N/A (Windows)",
            "python_version": f"{psutil.PROCFS_PATH if hasattr(psutil, 'PROCFS_PATH') else 'N/A'}",
        }
    except Exception as e:
        return {"error": str(e)}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Simple health check endpoint that returns basic application status",
    tags=["Health"]
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns application status, version, and uptime.
    This endpoint should always return 200 OK if the application is running.
    """
    current_time = time.time()
    uptime = current_time - app_start_time
    
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=current_time,
        uptime_seconds=uptime
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Comprehensive readiness check including dependencies and system status",
    tags=["Health"]
)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint.
    
    Verifies that the application is ready to serve requests by checking:
    - Critical dependencies are available
    - Data files are accessible
    - System resources are adequate
    
    Returns 200 OK if ready, 503 Service Unavailable if not ready.
    """
    current_time = time.time()
    uptime = current_time - app_start_time
    
    # Check dependencies
    dependencies = check_dependencies()
    system_info = get_system_info()
    
    # Determine if we're ready
    failed_deps = [name for name, status in dependencies.items() if status not in ["OK"]]
    
    if failed_deps:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready. Failed dependencies: {', '.join(failed_deps)}"
        )
    
    # Check system resources (more generous limit for scientific computing)
    if "memory_usage_mb" in system_info and system_info["memory_usage_mb"] > 4096:  # 4GB limit
        raise HTTPException(
            status_code=503,
            detail="Service not ready. High memory usage detected."
        )
    
    return ReadinessResponse(
        status="ready",
        version="2.0.0",
        timestamp=current_time,
        uptime_seconds=uptime,
        dependencies=dependencies,
        system=system_info
    )


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Application metrics",
    description="Basic application and system metrics for monitoring",
    tags=["Health"]
)
async def get_metrics() -> MetricsResponse:
    """
    Application metrics endpoint.
    
    Returns basic metrics useful for monitoring and alerting:
    - Uptime
    - Memory usage
    - CPU usage
    - Disk usage
    - Process information
    """
    current_time = time.time()
    uptime = current_time - app_start_time
    
    try:
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        disk_usage = psutil.disk_usage('/') if os.name != 'nt' else psutil.disk_usage('C:')
        
        return MetricsResponse(
            uptime_seconds=uptime,
            memory_usage_mb=memory_info.used / 1024 / 1024,
            cpu_percent=cpu_percent,
            disk_usage_percent=disk_usage.percent,
            python_version=f"{psutil.version_info}" if hasattr(psutil, 'version_info') else "unknown",
            process_id=os.getpid()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting metrics: {str(e)}"
        )


@router.get(
    "/performance",
    summary="Performance statistics",
    description="Detailed performance statistics from the performance monitoring middleware",
    tags=["Health"]
)
async def get_performance_stats(request: Request):
    """
    Performance statistics endpoint.
    
    Returns detailed performance metrics collected by the performance middleware:
    - Request counts and timing
    - Per-endpoint statistics
    - Slow request tracking
    - Overall performance metrics
    """
    try:
        # Get performance middleware from the app
        performance_middleware = None
        for middleware in request.app.user_middleware:
            if hasattr(middleware, 'cls') and 'PerformanceMiddleware' in str(middleware.cls):
                # Find the actual middleware instance
                performance_middleware = getattr(request.app, '_performance_middleware', None)
                break
        
        if performance_middleware:
            return performance_middleware.get_performance_stats()
        else:
            return {
                "error": "Performance middleware not found",
                "message": "Performance statistics are not available"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving performance stats: {str(e)}"
        )