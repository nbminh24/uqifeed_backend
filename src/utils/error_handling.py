import logging
from logging.handlers import RotatingFileHandler
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Optional, Union, Callable
import traceback
import json
import time
from datetime import datetime
import os
import uuid
import sys

# Configure logging with rotating file handler
log_file_path = "app_errors.log"
max_log_size = 10 * 1024 * 1024  # 10MB
backup_count = 5  # Keep 5 backup logs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(log_file_path, maxBytes=max_log_size, backupCount=backup_count),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("uqifeed")

# Custom exception classes
class APIError(Exception):
    """Base exception for API errors"""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        data: Dict[str, Any] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        self.data = data or {}


class ValidationError(APIError):
    """Exception for data validation errors"""
    def __init__(self, detail: str, data: Dict[str, Any] = None):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="VALIDATION_ERROR",
            data=data
        )


class NotFoundError(APIError):
    """Exception for resource not found errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="NOT_FOUND"
        )


class AuthenticationError(APIError):
    """Exception for authentication errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(APIError):
    """Exception for authorization errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="AUTHORIZATION_ERROR"
        )


class ConflictError(APIError):
    """Exception for conflict errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=409,
            detail=detail,
            error_code="CONFLICT"
        )


class RateLimitError(APIError):
    """Exception for rate limit errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=429,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED"
        )


class DatabaseError(APIError):
    """Exception for database errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="DATABASE_ERROR"
        )


class ExternalServiceError(APIError):
    """Exception for external service errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=502,
            detail=detail,
            error_code="EXTERNAL_SERVICE_ERROR"
        )


# Error handling middleware
async def error_handling_middleware(request: Request, call_next: Callable):
    """
    Middleware to handle exceptions and provide consistent error responses
    """
    start_time = time.time()
    
    try:
        # Process the request
        response = await call_next(request)
        return response
        
    except HTTPException as exc:
        # Handle FastAPI HTTP exceptions
        logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_host": request.client.host if request.client else None,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path
                }
            }
        )
    
    except APIError as exc:
        # Handle our custom API errors
        logger.error(
            f"API Error: {exc.status_code} - {exc.detail}",
            extra={
                "error_code": exc.error_code,
                "data": exc.data,
                "path": request.url.path,
                "method": request.method,
                "client_host": request.client.host if request.client else None,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.detail,
                    "data": exc.data,
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path
                }
            }
        )
    
    except Exception as exc:
        # Handle unexpected errors
        error_id = int(time.time())
        
        # Log detailed error information
        logger.critical(
            f"Unhandled Exception: {str(exc)} (Error ID: {error_id})",
            exc_info=True,
            extra={
                "error_id": error_id,
                "path": request.url.path,
                "method": request.method,
                "client_host": request.client.host if request.client else None,
                "traceback": traceback.format_exc()
            }
        )
        
        # Return a generic error response to the client
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "An unexpected error occurred",
                    "error_id": error_id,  # Include error ID for support reference
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path
                }
            }
        )


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security-related headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class APIMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track API metrics and performance"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Track route processing time
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests (over 1 second) for optimization
        if process_time > 1:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} - {process_time:.2f}s"
            )
            
        return response


# Helper functions for exception handling
def handle_api_error(func):
    """
    Decorator for API route handlers to handle exceptions consistently
    Works with both async and sync functions
    """
    import inspect
    
    if inspect.iscoroutinefunction(func):
        # For async functions
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except APIError:
                # Re-raise our custom exceptions for the middleware to handle
                raise
            except Exception as e:
                # Convert generic exceptions to APIError
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                raise APIError(f"Error processing request: {str(e)}")
        return async_wrapper
    else:
        # For sync functions
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except APIError:
                # Re-raise our custom exceptions for the middleware to handle
                raise
            except Exception as e:
                # Convert generic exceptions to APIError
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                raise APIError(f"Error processing request: {str(e)}")
        return sync_wrapper


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global error handler for all exceptions"""
    if isinstance(exc, APIError):
        logger.error(f"API Error: {exc.detail}", extra={
            "error_code": exc.error_code,
            "data": exc.data
        })
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.detail,
                    "data": exc.data
                }
            }
        )
    
    if isinstance(exc, HTTPException):
        logger.error(f"HTTP Error: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail
                }
            }
        )
    
    # Log unexpected errors
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )