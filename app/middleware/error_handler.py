"""
Error Handler Middleware

Provides comprehensive error handling, logging, and response formatting
for the FastAPI application. This middleware ensures consistent error
responses and proper logging of all errors.
"""

import logging
import traceback
import time
from typing import Any, Dict
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive error handling middleware that:
    - Catches and logs all unhandled exceptions
    - Formats error responses consistently
    - Adds request context to error logs
    - Handles different error types appropriately
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Log successful requests (INFO level)
            process_time = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Time: {process_time:.3f}s"
            )
            
            return response
            
        except HTTPException as exc:
            # Handle FastAPI HTTP exceptions (expected errors)
            process_time = time.time() - start_time
            logger.warning(
                f"HTTP Exception: {request.method} {request.url.path} "
                f"- Status: {exc.status_code} - Detail: {exc.detail} "
                f"- Time: {process_time:.3f}s"
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content=self._format_error_response(
                    status_code=exc.status_code,
                    error_type="HTTP_EXCEPTION",
                    message=exc.detail,
                    path=str(request.url.path),
                    method=request.method
                )
            )
            
        except ValueError as exc:
            # Handle validation and conversion errors
            process_time = time.time() - start_time
            logger.error(
                f"Validation Error: {request.method} {request.url.path} "
                f"- Error: {str(exc)} - Time: {process_time:.3f}s"
            )
            
            return JSONResponse(
                status_code=400,
                content=self._format_error_response(
                    status_code=400,
                    error_type="VALIDATION_ERROR",
                    message=f"Invalid input: {str(exc)}",
                    path=str(request.url.path),
                    method=request.method
                )
            )
            
        except ImportError as exc:
            # Handle missing dependencies
            process_time = time.time() - start_time
            logger.error(
                f"Import Error: {request.method} {request.url.path} "
                f"- Missing dependency: {str(exc)} - Time: {process_time:.3f}s"
            )
            
            return JSONResponse(
                status_code=503,
                content=self._format_error_response(
                    status_code=503,
                    error_type="DEPENDENCY_ERROR",
                    message="Service temporarily unavailable due to missing dependency",
                    path=str(request.url.path),
                    method=request.method
                )
            )
            
        except FileNotFoundError as exc:
            # Handle missing data files
            process_time = time.time() - start_time
            logger.error(
                f"File Not Found: {request.method} {request.url.path} "
                f"- Missing file: {str(exc)} - Time: {process_time:.3f}s"
            )
            
            return JSONResponse(
                status_code=503,
                content=self._format_error_response(
                    status_code=503,
                    error_type="DATA_FILE_ERROR",
                    message="Service temporarily unavailable due to missing data file",
                    path=str(request.url.path),
                    method=request.method
                )
            )
            
        except Exception as exc:
            # Handle all other unexpected errors
            process_time = time.time() - start_time
            error_trace = traceback.format_exc()
            
            logger.error(
                f"Unexpected Error: {request.method} {request.url.path} "
                f"- Error: {str(exc)} - Time: {process_time:.3f}s\n"
                f"Traceback:\n{error_trace}"
            )
            
            return JSONResponse(
                status_code=500,
                content=self._format_error_response(
                    status_code=500,
                    error_type="INTERNAL_ERROR",
                    message="An unexpected error occurred",
                    path=str(request.url.path),
                    method=request.method,
                    details=str(exc) if logger.level == logging.DEBUG else None
                )
            )

    def _format_error_response(
        self, 
        status_code: int, 
        error_type: str, 
        message: str, 
        path: str, 
        method: str,
        details: str = None
    ) -> Dict[str, Any]:
        """
        Format a consistent error response structure.
        """
        response = {
            "error": {
                "type": error_type,
                "message": message,
                "status_code": status_code,
                "timestamp": time.time(),
                "path": path,
                "method": method
            }
        }
        
        if details and logger.level == logging.DEBUG:
            response["error"]["details"] = details
            
        return response