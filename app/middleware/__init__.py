"""
FastAPI Middleware Package

This package contains custom middleware for the FastAPI application.
Middleware provides cross-cutting concerns like error handling, logging,
performance monitoring, and request validation.

Available middleware:
- error_handler: Comprehensive error handling and logging
- performance: Request timing and performance monitoring
- security: Rate limiting and security headers
"""

from .error_handler import ErrorHandlerMiddleware
from .performance import PerformanceMiddleware
from .security import RateLimitMiddleware, SecurityHeadersMiddleware

__all__ = ["ErrorHandlerMiddleware", "PerformanceMiddleware", "RateLimitMiddleware", "SecurityHeadersMiddleware"]