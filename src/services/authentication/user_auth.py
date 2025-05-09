from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from datetime import datetime
from typing import Optional, Dict
from bson import ObjectId
import asyncio
import logging

from src.config.database import users_collection
from src.schemas.user.user_schema import UserCreate
from src.services.authentication.password_manager import get_password_hash
from config import config

logger = logging.getLogger(__name__)

# JWT token setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

async def create_user(user_data: UserCreate):
    """
    Create a new user with validation
    """
    try:
        # Check if user already exists
        existing_user = await users_collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Create new user
        user_dict = user_data.dict()
        user_dict["password"] = get_password_hash(user_dict["password"])
        user_dict["created_at"] = datetime.utcnow()
        
        # Insert into database
        result = await users_collection.insert_one(user_dict)
        
        # Return created user without password
        created_user = await users_collection.find_one({"_id": result.inserted_id})
        created_user["id"] = str(created_user["_id"])
        
        # Remove sensitive fields
        created_user.pop("password", None)
        
        return created_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

async def get_user_token_preference(user_id: str) -> str:
    """
    Get user's token expiration preference with validation
    """
    try:
        # Check if user has a preference stored
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        if "token_preference" in user:
            return user["token_preference"]
        
        # Return default if no preference is set
        return "default"
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token preference: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

async def set_user_token_preference(user_id: str, preference: str):
    """
    Set user's token expiration preference with validation
    """
    try:
        valid_preferences = ["short", "default", "extended", "long", "very-long"]
        if preference not in valid_preferences:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid preference. Must be one of: {', '.join(valid_preferences)}"
            )
        
        # Update user's preference
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"token_preference": preference}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return {"message": "Token preference updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting token preference: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current authenticated user from token with validation
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await users_collection.find_one({"email": email})
    if user is None:
        raise credentials_exception
    
    # Convert ObjectId to string
    user["id"] = str(user["_id"])
    
    return user

async def get_current_user_ws(websocket: WebSocket, user_id: str) -> Optional[Dict]:
    """
    Authenticate user for WebSocket connection with timeout
    """
    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            logger.error("No token provided for WebSocket connection")
            return None
            
        # Set timeout for authentication
        try:
            await asyncio.wait_for(websocket.accept(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.error("WebSocket authentication timeout")
            return None
            
        # Verify token
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            user_id_from_token = payload.get("sub")
        except JWTError as e:
            logger.error(f"Invalid token for WebSocket connection: {str(e)}")
            return None
        
        if not user_id_from_token or user_id_from_token != user_id:
            logger.error("Token user ID mismatch")
            return None
            
        # Get user from database
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            logger.error("User not found for WebSocket connection")
            return None
            
        return user
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        return None