from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple
import time
from src.utils.error_handling import RateLimitError, ERROR_MESSAGES

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_limit: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.requests: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get client IP
        client_ip = request.client.host
        
        # Initialize request tracking for this IP
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Clean old requests
        current_time = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 60
        ]
        
        # Check rate limits
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise RateLimitError(
                ERROR_MESSAGES["rate_limit"],
                details={
                    "retry_after": 60,
                    "limit": self.requests_per_minute,
                    "window": "1 minute"
                }
            )
        
        # Check burst limit
        recent_requests = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 1
        ]
        if len(recent_requests) >= self.burst_limit:
            raise RateLimitError(
                ERROR_MESSAGES["rate_limit"],
                details={
                    "retry_after": 1,
                    "limit": self.burst_limit,
                    "window": "1 second"
                }
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_ip])
        )
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response 