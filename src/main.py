from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

from src.routes.user_router import router as user_router
from src.routes.food_router import router as food_router
from src.routes.calorie_router import nutrition_router, calorie_router
from src.routes.social_auth_router import social_auth_router
from src.routes.measurement_units_router import router as measurement_units_router
from src.routes.notification_router import router as notification_router
from src.utils.error_handling import error_handling_middleware
from src.config.database import initialize_database, initialize_meal_type_standards

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)

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

# Include routers
app.include_router(user_router)
app.include_router(food_router)
app.include_router(nutrition_router)
app.include_router(calorie_router)
app.include_router(social_auth_router)
app.include_router(measurement_units_router)
app.include_router(notification_router)

@app.on_event("startup")
async def startup_db_client():
    """Initialize database connection and setup on application startup"""
    await initialize_database()
    await initialize_meal_type_standards()

@app.get("/")
async def root():
    """Root endpoint to check if the API is running"""
    return {
        "message": "Welcome to UQIFeed API",
        "version": config.API_VERSION,
        "status": "online",
        "documentation": "/docs",
        "database": "MongoDB"
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run("src.main:app", host=config.HOST, port=config.PORT, reload=config.DEBUG)
