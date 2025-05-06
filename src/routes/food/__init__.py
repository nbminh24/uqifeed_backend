from fastapi import APIRouter
from .food_detection_routes import router as detection_router
from .food_service_routes import router as database_router

# Main food router
food_router = APIRouter(
    prefix="/foods",
    tags=["foods"]
)

# Include sub-routers
food_router.include_router(database_router)
food_router.include_router(detection_router, prefix="/detection")

# Export the main router
__all__ = ["food_router"]