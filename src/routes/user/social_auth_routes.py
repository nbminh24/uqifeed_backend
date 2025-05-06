from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import Optional
import config
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.services.authentication.social_auth import (
    verify_google_token,
    get_facebook_user_info,
    authenticate_social_user,
    exchange_oauth_code
)

# Initialize social_auth_routes
social_auth_routes = APIRouter(
    prefix="/auth",
    tags=["social_auth"]
)

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

@social_auth_routes.post("/google/token")
@limiter.limit(config.RATE_LIMIT_LOGIN)
async def login_with_google_token(request: Request, id_token: str):
    """
    Login with Google ID token (client-side flow)
    
    This endpoint is used when authentication is done on the client side 
    and the ID token is sent directly to the backend
    """
    try:
        # Verify the Google token
        user_info = await verify_google_token(id_token)
        
        # Authenticate or create user
        auth_result = await authenticate_social_user(user_info)
        
        return {
            "access_token": auth_result["access_token"],
            "token_type": "bearer",
            "user": auth_result["user"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Google authentication failed: {str(e)}"
        )

@social_auth_routes.post("/facebook/token")
@limiter.limit(config.RATE_LIMIT_LOGIN)
async def login_with_facebook_token(request: Request, access_token: str):
    """
    Login with Facebook access token (client-side flow)
    
    This endpoint is used when authentication is done on the client side 
    and the access token is sent directly to the backend
    """
    try:
        # Get user info from Facebook
        user_info = await get_facebook_user_info(access_token)
        
        # Authenticate or create user
        auth_result = await authenticate_social_user(user_info)
        
        return {
            "access_token": auth_result["access_token"],
            "token_type": "bearer",
            "user": auth_result["user"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Facebook authentication failed: {str(e)}"
        )

@social_auth_routes.get("/google/callback")
@limiter.limit(config.RATE_LIMIT_LOGIN)
async def google_oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    redirect_uri: Optional[str] = Query(None, description="Redirect URI used in client")
):
    """
    Handle Google OAuth callback (server-side flow)
    
    This endpoint is used when the client redirects to Google for authentication
    and Google redirects back to this endpoint with an authorization code
    """
    try:
        # Exchange code for token and authenticate user
        auth_result = await exchange_oauth_code("google", code, redirect_uri)
        
        return {
            "access_token": auth_result["access_token"],
            "token_type": "bearer",
            "user": auth_result["user"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Google OAuth callback failed: {str(e)}"
        )

@social_auth_routes.get("/facebook/callback")
@limiter.limit(config.RATE_LIMIT_LOGIN)
async def facebook_oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Facebook"),
    redirect_uri: Optional[str] = Query(None, description="Redirect URI used in client")
):
    """
    Handle Facebook OAuth callback (server-side flow)
    
    This endpoint is used when the client redirects to Facebook for authentication
    and Facebook redirects back to this endpoint with an authorization code
    """
    try:
        # Exchange code for token and authenticate user
        auth_result = await exchange_oauth_code("facebook", code, redirect_uri)
        
        return {
            "access_token": auth_result["access_token"],
            "token_type": "bearer",
            "user": auth_result["user"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Facebook OAuth callback failed: {str(e)}"
        )