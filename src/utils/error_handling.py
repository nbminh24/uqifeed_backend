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

class BaseAPIError(Exception):
    """Base class for API errors"""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class NotFoundError(BaseAPIError):
    """Error for when a resource is not found"""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)

class ValidationError(BaseAPIError):
    """Error for validation failures"""
    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)

class AuthorizationError(BaseAPIError):
    """Error for authorization failures"""
    def __init__(self, message: str = "Not authorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)

class AuthenticationError(BaseAPIError):
    """Error for authentication failures"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)

class RateLimitError(BaseAPIError):
    """Error for rate limiting"""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS, details)

class FileUploadError(BaseAPIError):
    """Error for file upload issues"""
    def __init__(self, message: str = "File upload failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)

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
    
    except BaseAPIError as exc:
        # Handle our custom API errors
        logger.error(
            f"API Error: {exc.status_code} - {exc.message}",
            extra={
                "details": exc.details,
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
                    "message": exc.message,
                    "details": exc.details,
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


def handle_api_error(func):
    """Decorator to handle API errors"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BaseAPIError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "message": e.message,
                    "details": e.details
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Internal server error",
                    "details": str(e)
                }
            )
    return wrapper


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global error handler for all exceptions"""
    if isinstance(exc, BaseAPIError):
        logger.error(f"API Error: {exc.message}", extra={
            "details": exc.details
        })
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.message,
                    "details": exc.details
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

# Error messages
ERROR_MESSAGES = {
    "not_found": "The requested resource was not found",
    "validation_error": "Invalid input data",
    "auth_error": "Authentication failed",
    "auth_required": "Authentication required",
    "forbidden": "Not authorized to perform this action",
    "rate_limit": "Too many requests, please try again later",
    "file_upload": {
        "invalid_type": "Invalid file type",
        "too_large": "File size exceeds limit",
        "upload_failed": "File upload failed"
    },
    "db_operation_failed": "Database operation failed: {error}",
    "invalid_date": "Invalid date format. Use YYYY-MM-DD",
    "invalid_meal_type": "Invalid meal type",
    "invalid_nutrition": "Invalid nutrition values",
    "invalid_ingredient": "Invalid ingredient data"
}