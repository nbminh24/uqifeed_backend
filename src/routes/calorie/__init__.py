from fastapi import APIRouter
from .calorie_routes import router as calorie_router

# Main calorie router
router = APIRouter(
    prefix="/calorie",
    tags=["calorie"]
)

# Include sub-routers
router.include_router(calorie_router)

# Export the main router
__all__ = ["router"]