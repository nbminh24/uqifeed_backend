from fastapi import APIRouter
from .notification_routes import router as notification_router

# Main notification router
router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)

# Include sub-routers
router.include_router(notification_router)

# Export the main router
__all__ = ["router"]