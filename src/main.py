from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Import using new structure
from src.routes.user import user_router
from src.routes.user.social_auth_routes import social_auth_routes
from src.routes.food import food_router
from src.routes.calorie.calorie_routes import router as calorie_router
from src.routes.notification import router as notification_router
from src.routes.dish import router as dish_router
from src.utils.error_handling import error_handling_middleware, SecureHeadersMiddleware, APIMetricsMiddleware
from src.config.database import initialize_database, initialize_meal_type_standards, client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app_errors.log'
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add security and performance middlewares
app.add_middleware(SecureHeadersMiddleware)
app.add_middleware(APIMetricsMiddleware)

# Add custom error handling middleware
app.middleware("http")(error_handling_middleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        # Log errors
        logger.error(f"Error processing request: {str(e)}")
        process_time = time.time() - start_time
        error_response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
        error_response.headers["X-Process-Time"] = str(process_time)
        return error_response

# Include routers
app.include_router(user_router)
app.include_router(food_router)
app.include_router(calorie_router)
app.include_router(social_auth_routes)
app.include_router(notification_router)
app.include_router(dish_router)

@app.on_event("startup")
async def startup_db_client():
    """Initialize database connection and setup on application startup"""
    try:
        # Initialize database connection and indexes
        db_initialized = await initialize_database()
        if db_initialized:
            # Only initialize meal type standards if database connection is successful
            await initialize_meal_type_standards()
            logger.info("Application startup completed successfully")
        else:
            logger.critical("Database initialization failed")
    except Exception as e:
        logger.critical(f"Error during application startup: {str(e)}")
        # In production, we might want to exit the application here if database connection fails
        # But for development, we'll just log the error and continue
        if not config.DEBUG:
            logger.critical("Database connection critical error in production mode, exiting application")
            import sys
            sys.exit(1)

# Root endpoint
@app.get("/", tags=["Root"])
@limiter.limit("10/minute")
async def root(request: Request):
    """Root endpoint"""
    return {
        "message": "Welcome to UqiFeed API",
        "version": config.API_VERSION,
        "status": "online",
        "documentation": "/docs",
        "server_time": datetime.now().isoformat()
    }

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint"""
    try:
        # Check database connection
        await client.server_info()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": db_status
    }

# Custom OpenAPI schema for better documentation
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=config.API_TITLE,
        version=config.API_VERSION,
        description=config.API_DESCRIPTION,
        routes=app.routes,
    )
    
    # Add security schemes (for JWT authentication)
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token"
        }
    }
    
    # Add global security requirement (most endpoints require authentication)
    openapi_schema["security"] = [{"Bearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=config.HOST, port=config.PORT, reload=config.DEBUG)
