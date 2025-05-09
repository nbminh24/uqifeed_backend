from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import logging
from datetime import datetime

from src.routes import (
    auth_router,
    food_router,
    dish_router,
    calorie_router,
    nutrition_router,
    profile_router,
    notification_router,
    settings_router,
    meal_plan_router,
    social_router,
    progress_router,
    achievement_router
)
from src.middleware.rate_limit import RateLimitMiddleware
from src.middleware.validation import RequestValidationMiddleware, QueryParamValidationMiddleware
from src.middleware.monitoring import MetricsMiddleware
from src.utils.error_handling import BaseAPIError, error_handler
from src.utils.monitoring import ResourceMetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("uqifeed")

# Initialize FastAPI app
app = FastAPI(
    title="Uqifeed API",
    description="Backend API for Uqifeed nutrition tracking application",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    burst_limit=10
)

# Add request validation middleware
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(QueryParamValidationMiddleware)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(food_router, prefix="/foods", tags=["foods"])
app.include_router(dish_router, prefix="/dishes", tags=["dishes"])
app.include_router(calorie_router, prefix="/calories", tags=["calories"])
app.include_router(nutrition_router, prefix="/nutrition", tags=["nutrition"])
app.include_router(profile_router, prefix="/profile", tags=["profile"])
app.include_router(notification_router, prefix="/notifications", tags=["notifications"])
app.include_router(settings_router, prefix="/settings", tags=["settings"])
app.include_router(meal_plan_router, prefix="/meal-plans", tags=["meal-plans"])
app.include_router(social_router, prefix="/social", tags=["social"])
app.include_router(progress_router, prefix="/progress", tags=["progress"])
app.include_router(achievement_router, prefix="/achievements", tags=["achievements"])

# Add error handler
app.add_exception_handler(BaseAPIError, error_handler)

@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    # Collect resource metrics
    ResourceMetricsCollector.collect_metrics()
    metrics = ResourceMetricsCollector.get_metrics()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics
    }

# Start resource metrics collection
@app.on_event("startup")
async def startup_event():
    """Start resource metrics collection on startup"""
    ResourceMetricsCollector.collect_metrics()
