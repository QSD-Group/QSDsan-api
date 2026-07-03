"""
Shared FastAPI app construction: middleware, CORS, and error handlers.

Used by app/main.py (the "everything" local-dev entrypoint) and by each of
the four app/entrypoints/*.py Lambda entrypoints, so all four deployables
get identical error-handling/CORS/security behavior without duplicating it
four times. Callers register their own routers after calling create_app().
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.middleware import (
    ErrorHandlerMiddleware,
    PerformanceMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware
)

# env-driven allowlist, default-closed to the known frontends.
# Set ALLOWED_ORIGINS (comma-separated) in production to override the default.
# NOTE: "*" + allow_credentials=True is rejected by browsers, so origins are explicit.
_DEFAULT_ALLOWED_ORIGINS = (
    "https://nj-bioenergy.apps.qsdsan.com,"  # group-owned frontend
    "http://localhost:8000,http://localhost:3000"  # local dev
)
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ALLOWED_ORIGINS).split(",")
    if o.strip()
]


def create_app(title: str = "Waste-to-Energy Processing API") -> FastAPI:
    app = FastAPI(
        title=title,
        description="High-performance API for waste-to-energy calculations",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Order matters - last added runs first.
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(PerformanceMiddleware, slow_request_threshold=0.5)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=30, requests_per_hour=500)
    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.exception_handler(500)
    async def internal_error_handler(request, exc):
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    return app
