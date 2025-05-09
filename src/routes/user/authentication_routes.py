from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Optional
import config
from slowapi import Limiter
from slowapi.util import get_remote_address
import jwt
from pydantic import BaseModel
from src.services.authentication.jwt_handler import create_access_token, create_refresh_token
from src.services.authentication.password_manager import authenticate_user
from src.services.authentication.user_auth import create_user, get_current_user, get_user_token_preference, set_user_token_preference
from src.schemas.user.user_schema import UserCreate, UserResponse
from src.services.user.user_service import UserService
from src.utils.rate_limiter import rate_limit
from src.utils.error_handler import handle_error
from src.config.settings import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from facebook import GraphAPI
import httpx

# Initialize router
router = APIRouter(
    tags=["authentication"]
)

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

@router.post("/auth/google")
@handle_error
@rate_limit(max_requests=5, window_seconds=60)
async def google_auth(request: Request):
    """
    Authenticate user with Google
    """
    try:
        data = await request.json()
        token = data.get("token")
        
        # Verify Google token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(status_code=400, detail="Invalid token issuer")
            
        # Get user info
        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')
        
        # Check if user exists
        user = await UserService.get_user_by_email(email)
        
        if not user:
            # Create new user
            user_data = {
                "email": email,
                "name": name,
                "profile_picture": picture,
                "auth_provider": "google"
            }
            user = await UserService.create_user(user_data)
        
        # Generate tokens
        access_token = create_access_token(user["_id"])
        refresh_token = create_refresh_token(user["_id"])
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auth/facebook")
@handle_error
@rate_limit(max_requests=5, window_seconds=60)
async def facebook_auth(request: Request):
    """
    Authenticate user with Facebook
    """
    try:
        data = await request.json()
        access_token = data.get("access_token")
        
        # Verify Facebook token
        graph = GraphAPI(access_token=access_token)
        user_info = graph.get_object(
            id='me',
            fields='id,email,name,picture'
        )
        
        if not user_info.get('email'):
            raise HTTPException(status_code=400, detail="Email not provided by Facebook")
            
        # Get user info
        email = user_info['email']
        name = user_info.get('name', '')
        picture = user_info.get('picture', {}).get('data', {}).get('url', '')
        
        # Check if user exists
        user = await UserService.get_user_by_email(email)
        
        if not user:
            # Create new user
            user_data = {
                "email": email,
                "name": name,
                "profile_picture": picture,
                "auth_provider": "facebook"
            }
            user = await UserService.create_user(user_data)
        
        # Generate tokens
        access_token = create_access_token(user["_id"])
        refresh_token = create_refresh_token(user["_id"])
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))