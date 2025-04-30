import logging
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, Union, Callable
import traceback
import json
import time
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app_errors.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("uqifeed")

# Custom exception classes
class APIError(Exception):
    """Base exception for API errors"""
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ValidationError(APIError):
    """Exception for data validation errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class NotFoundError(APIError):
    """Exception for resource not found errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)


class AuthenticationError(APIError):
    """Exception for authentication errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)


class AuthorizationError(APIError):
    """Exception for authorization errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)


class DatabaseError(APIError):
    """Exception for database errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


class ExternalAPIError(APIError):
    """Exception for external API errors (e.g. Gemini API)"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_502_BAD_GATEWAY, details)


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


# Helper functions for exception handling
def handle_api_error(func):
    """
    Decorator for API route handlers to handle exceptions consistently
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except APIError:
            # Re-raise our custom exceptions for the middleware to handle
            raise
        except Exception as e:
            # Convert generic exceptions to APIError
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise APIError(f"Error processing request: {str(e)}")
    
    return wrapper