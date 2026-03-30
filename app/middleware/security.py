"""
Security Middleware

Provides security enhancements including rate limiting, request validation,
and security headers for the FastAPI application.
"""

import time
import hashlib
from collections import defaultdict, deque
from typing import Dict, Tuple
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware that tracks requests per IP address.
    """
    
    def __init__(
        self, 
        app, 
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        
        # Store request timestamps for each IP
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=requests_per_day))
        
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get client IP
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests and check rate limits
        self._clean_old_requests(client_ip, current_time)
        
        if self._is_rate_limited(client_ip, current_time):
            return self._rate_limit_response()
        
        # Record this request
        self.request_history[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, client_ip, current_time)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers first (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _clean_old_requests(self, client_ip: str, current_time: float):
        """Remove requests older than 24 hours"""
        if client_ip not in self.request_history:
            return
            
        cutoff_time = current_time - 86400  # 24 hours ago
        history = self.request_history[client_ip]
        
        # Remove old entries
        while history and history[0] < cutoff_time:
            history.popleft()
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client has exceeded rate limits"""
        if client_ip not in self.request_history:
            return False
        
        history = list(self.request_history[client_ip])
        
        # Check minute limit
        minute_ago = current_time - 60
        minute_count = sum(1 for t in history if t > minute_ago)
        if minute_count >= self.requests_per_minute:
            return True
        
        # Check hour limit
        hour_ago = current_time - 3600
        hour_count = sum(1 for t in history if t > hour_ago)
        if hour_count >= self.requests_per_hour:
            return True
        
        # Check day limit
        day_ago = current_time - 86400
        day_count = sum(1 for t in history if t > day_ago)
        if day_count >= self.requests_per_day:
            return True
        
        return False
    
    def _rate_limit_response(self) -> Response:
        """Return rate limit exceeded response"""
        return Response(
            content='{"error": {"type": "RATE_LIMIT_EXCEEDED", "message": "Rate limit exceeded. Please try again later."}}',
            status_code=429,
            headers={
                "Content-Type": "application/json",
                "Retry-After": "60"
            }
        )
    
    def _add_rate_limit_headers(self, response: Response, client_ip: str, current_time: float):
        """Add rate limit information to response headers"""
        if client_ip not in self.request_history:
            return
        
        history = list(self.request_history[client_ip])
        
        # Calculate remaining requests
        minute_ago = current_time - 60
        minute_count = sum(1 for t in history if t > minute_ago)
        
        hour_ago = current_time - 3600
        hour_count = sum(1 for t in history if t > hour_ago)
        
        response.headers["X-RateLimit-Minute-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Minute-Remaining"] = str(max(0, self.requests_per_minute - minute_count))
        response.headers["X-RateLimit-Hour-Limit"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Hour-Remaining"] = str(max(0, self.requests_per_hour - hour_count))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        # Only add HSTS in production
        if not request.url.hostname in ["localhost", "127.0.0.1"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response