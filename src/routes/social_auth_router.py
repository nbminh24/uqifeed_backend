from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from typing import Optional
import os
from datetime import datetime

from src.config.database import users_collection
from src.services.auth_service import create_access_token, get_current_user, set_user_token_preference
from src.schemas.schemas import UserResponse

# Khởi tạo router
social_auth_router = APIRouter(
    prefix="/auth",
    tags=["social-auth"]
)

# Các biến môi trường cho OAuth (trong thực tế, đặt trong file config hoặc .env)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your-google-client-id")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "your-google-client-secret")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "your-facebook-app-id")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "your-facebook-app-secret")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8000/auth/facebook/callback")

APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "your-apple-client-id")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID", "your-apple-team-id")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID", "your-apple-key-id")
APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY", "your-apple-private-key")
APPLE_REDIRECT_URI = os.getenv("APPLE_REDIRECT_URI", "http://localhost:8000/auth/apple/callback")

# Google OAuth routes
@social_auth_router.get("/google")
async def login_google():
    """Redirect to Google OAuth login page"""
    google_auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=email%20profile&access_type=offline"
    return RedirectResponse(url=google_auth_url)

@social_auth_router.get("/google/callback")
async def google_callback(code: str, request: Request):
    """Handle Google OAuth callback"""
    try:
        # Trong thực tế, trao đổi mã xác thực để lấy token
        # Sau đó lấy thông tin người dùng từ Google API
        # Đây là mã giả để demo
        
        # Mock user data
        google_user = {
            "email": "user@example.com",
            "name": "Google User",
            "picture": "https://example.com/profile.jpg"
        }
        
        # Kiểm tra xem người dùng đã tồn tại chưa
        user = await users_collection.find_one({"email": google_user["email"]})
        
        if not user:
            # Tạo người dùng mới nếu chưa tồn tại
            user_data = {
                "email": google_user["email"],
                "name": google_user["name"],
                "profile_image": google_user["picture"],
                "auth_provider": "google",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await users_collection.insert_one(user_data)
            user = await users_collection.find_one({"_id": result.inserted_id})
        
        # Tạo JWT token
        access_token = create_access_token(
            data={"sub": user["email"]},
            user_preference="default"
        )
        
        # Trong ứng dụng thực tế, chuyển hướng về frontend với token
        frontend_redirect_url = f"http://localhost:3000/auth-callback?token={access_token}&provider=google"
        return RedirectResponse(url=frontend_redirect_url)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}"
        )

# Facebook OAuth routes
@social_auth_router.get("/facebook")
async def login_facebook():
    """Redirect to Facebook OAuth login page"""
    facebook_auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?client_id={FACEBOOK_APP_ID}&redirect_uri={FACEBOOK_REDIRECT_URI}&scope=email,public_profile"
    return RedirectResponse(url=facebook_auth_url)

@social_auth_router.get("/facebook/callback")
async def facebook_callback(code: str, request: Request):
    """Handle Facebook OAuth callback"""
    try:
        # Trong thực tế, trao đổi mã xác thực để lấy token
        # Sau đó lấy thông tin người dùng từ Facebook API
        # Đây là mã giả để demo
        
        # Mock user data
        facebook_user = {
            "email": "user@example.com",
            "name": "Facebook User",
            "picture": "https://example.com/profile.jpg"
        }
        
        # Kiểm tra xem người dùng đã tồn tại chưa
        user = await users_collection.find_one({"email": facebook_user["email"]})
        
        if not user:
            # Tạo người dùng mới nếu chưa tồn tại
            user_data = {
                "email": facebook_user["email"],
                "name": facebook_user["name"],
                "profile_image": facebook_user["picture"],
                "auth_provider": "facebook",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await users_collection.insert_one(user_data)
            user = await users_collection.find_one({"_id": result.inserted_id})
        
        # Tạo JWT token
        access_token = create_access_token(
            data={"sub": user["email"]},
            user_preference="default"
        )
        
        # Trong ứng dụng thực tế, chuyển hướng về frontend với token
        frontend_redirect_url = f"http://localhost:3000/auth-callback?token={access_token}&provider=facebook"
        return RedirectResponse(url=frontend_redirect_url)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Facebook authentication failed: {str(e)}"
        )

# Apple OAuth routes
@social_auth_router.get("/apple")
async def login_apple():
    """Redirect to Apple OAuth login page"""
    apple_auth_url = f"https://appleid.apple.com/auth/authorize?client_id={APPLE_CLIENT_ID}&redirect_uri={APPLE_REDIRECT_URI}&response_type=code&scope=name%20email&response_mode=form_post"
    return RedirectResponse(url=apple_auth_url)

@social_auth_router.post("/apple/callback")
async def apple_callback(code: str, request: Request):
    """Handle Apple OAuth callback"""
    try:
        # Trong thực tế, trao đổi mã xác thực để lấy token
        # Sau đó lấy thông tin người dùng từ Apple API
        # Đây là mã giả để demo
        
        # Mock user data
        apple_user = {
            "email": "user@example.com",
            "name": "Apple User",
            "picture": None
        }
        
        # Kiểm tra xem người dùng đã tồn tại chưa
        user = await users_collection.find_one({"email": apple_user["email"]})
        
        if not user:
            # Tạo người dùng mới nếu chưa tồn tại
            user_data = {
                "email": apple_user["email"],
                "name": apple_user["name"],
                "profile_image": apple_user["picture"],
                "auth_provider": "apple",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await users_collection.insert_one(user_data)
            user = await users_collection.find_one({"_id": result.inserted_id})
        
        # Tạo JWT token
        access_token = create_access_token(
            data={"sub": user["email"]},
            user_preference="default"
        )
        
        # Trong ứng dụng thực tế, chuyển hướng về frontend với token
        frontend_redirect_url = f"http://localhost:3000/auth-callback?token={access_token}&provider=apple"
        return RedirectResponse(url=frontend_redirect_url)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Apple authentication failed: {str(e)}"
        )