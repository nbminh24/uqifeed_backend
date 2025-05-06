from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
import config
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.services.authentication.jwt_handler import create_access_token
from src.services.authentication.password_manager import authenticate_user
from src.services.authentication.user_auth import create_user, get_current_user, get_user_token_preference, set_user_token_preference
from src.schemas.user.user_schema import UserCreate, UserResponse

# Initialize router
router = APIRouter(
    tags=["authentication"]
)

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

# Public routes (no authentication required)
@router.post("/register", response_model=UserResponse)
@limiter.limit(config.RATE_LIMIT_LOGIN)
async def register(request: Request, user: UserCreate):
    """Register a new user"""
    return await create_user(user)

@router.post("/login")
@limiter.limit(config.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session_type: Optional[str] = Query(None, description="Session duration preference: 'short', 'default', 'extended', or 'long'")
):
    """Login and get access token with configurable expiration time"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # If session_type is provided, use it, otherwise get stored preference
    token_preference = session_type
    if not token_preference:
        token_preference = await get_user_token_preference(user["id"])
    
    # Create token with user preference
    access_token = create_access_token(
        data={"sub": user["email"]},
        user_preference=token_preference
    )
    
    # If user provided a session type preference, save it for future logins
    if session_type:
        await set_user_token_preference(user["id"], session_type)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user["id"], 
        "name": user["name"],
        "session_type": token_preference
    }

@router.post("/token-preference")
async def update_token_preference(
    preference: str = Query(..., description="Session preference: 'short', 'default', 'extended', or 'long'"),
    current_user = Depends(get_current_user)
):
    """Update user's token expiration preference for future logins"""
    result = await set_user_token_preference(current_user["id"], preference)
    return result

# Protected routes (authentication required)
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user = Depends(get_current_user)):
    """Get current user's information"""
    return current_user