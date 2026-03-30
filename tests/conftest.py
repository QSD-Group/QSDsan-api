"""
Shared fixtures for all test modules.

The TestClient is session-scoped to avoid re-importing the heavy scientific
libraries (exposan, biosteam, etc.) on every test.

Rate limiting is disabled for the test session — the middleware would exhaust
the 30 req/min limit across the full test suite and cause false 429 failures.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from app.main import app
    from app.middleware.security import RateLimitMiddleware

    # Disable rate limiting so the test suite doesn't hit its own limits
    RateLimitMiddleware._is_rate_limited = lambda self, client_ip, current_time: False

    return TestClient(app)
