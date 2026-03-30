"""
Performance Monitoring Middleware

Tracks request performance metrics, response times, and provides
performance insights for the FastAPI application.
"""

import time
import logging
from typing import Dict, List
from collections import defaultdict, deque
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware that:
    - Tracks request response times
    - Monitors slow requests
    - Collects endpoint performance metrics
    - Adds timing headers to responses
    """

    def __init__(self, app, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        
        # Performance metrics storage (in-memory for now)
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.slow_requests: deque = deque(maxlen=50)
        self.total_requests = 0
        self.total_time = 0.0

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate timing
        process_time = time.time() - start_time
        endpoint = f"{request.method} {request.url.path}"
        
        # Update metrics
        self._update_metrics(endpoint, process_time, request, response)
        
        # Add timing headers
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        response.headers["X-Timestamp"] = str(start_time)
        
        # Log slow requests
        if process_time > self.slow_request_threshold:
            self._log_slow_request(endpoint, process_time, request)
        
        return response

    def _update_metrics(self, endpoint: str, process_time: float, request: Request, response: Response):
        """Update performance metrics"""
        # Track per-endpoint timing
        self.request_times[endpoint].append(process_time)
        
        # Track overall metrics
        self.total_requests += 1
        self.total_time += process_time
        
        # Track slow requests
        if process_time > self.slow_request_threshold:
            self.slow_requests.append({
                "endpoint": endpoint,
                "time": process_time,
                "timestamp": time.time(),
                "status_code": response.status_code,
                "user_agent": request.headers.get("user-agent", "unknown")
            })

    def _log_slow_request(self, endpoint: str, process_time: float, request: Request):
        """Log slow requests for monitoring"""
        logger.warning(
            f"Slow request detected: {endpoint} "
            f"- Time: {process_time:.3f}s "
            f"- Threshold: {self.slow_request_threshold}s "
            f"- User-Agent: {request.headers.get('user-agent', 'unknown')}"
        )

    def get_performance_stats(self) -> Dict:
        """Get current performance statistics"""
        stats = {
            "total_requests": self.total_requests,
            "average_response_time": self.total_time / max(self.total_requests, 1),
            "slow_request_count": len(self.slow_requests),
            "slow_request_threshold": self.slow_request_threshold
        }
        
        # Per-endpoint statistics
        endpoint_stats = {}
        for endpoint, times in self.request_times.items():
            if times:
                times_list = list(times)
                endpoint_stats[endpoint] = {
                    "count": len(times_list),
                    "average_time": sum(times_list) / len(times_list),
                    "min_time": min(times_list),
                    "max_time": max(times_list),
                    "recent_times": times_list[-10:]  # Last 10 requests
                }
        
        stats["endpoints"] = endpoint_stats
        stats["recent_slow_requests"] = list(self.slow_requests)[-10:]  # Last 10 slow requests
        
        return stats