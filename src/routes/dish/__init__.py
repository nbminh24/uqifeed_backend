from fastapi import APIRouter
from .dish_routes import router as dish_router

# Main dish router
router = APIRouter(
    prefix="/dishes",
    tags=["dishes"]
)

# Include sub-routers
router.include_router(dish_router)

# Export the main router
__all__ = ["router"]