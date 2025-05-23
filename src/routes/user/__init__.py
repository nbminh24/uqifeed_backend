from fastapi import APIRouter
from .authentication_routes import router as auth_router
from .profile_management_routes import router as profile_router
from .nutrition_goals_routes import router as nutrition_router

# Main user router
user_router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# Include sub-routers
user_router.include_router(auth_router)
user_router.include_router(profile_router, prefix="/profile")
user_router.include_router(nutrition_router, prefix="/profile")

# Export the main router
__all__ = ["user_router"]