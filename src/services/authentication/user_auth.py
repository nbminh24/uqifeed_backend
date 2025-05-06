from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from datetime import datetime
from typing import Optional
from bson import ObjectId

from src.config.database import users_collection
from src.schemas.user.user_schema import UserCreate
from src.services.authentication.password_manager import get_password_hash
from config import config

# JWT token setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

async def create_user(user_data: UserCreate):
    """
    Create a new user
    
    Args:
        user_data: User creation data
    
    Returns:
        dict: Created user
    """
    # Check if user already exists
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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

async def get_user_token_preference(user_id: str) -> str:
    """
    Get user's token expiration preference
    
    Args:
        user_id: User ID
        
    Returns:
        str: Token preference ('short', 'default', 'extended', 'long')
    """
    # Check if user has a preference stored
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user and "token_preference" in user:
        return user["token_preference"]
    
    # Return default if no preference is set
    return "default"

async def set_user_token_preference(user_id: str, preference: str):
    """
    Set user's token expiration preference
    
    Args:
        user_id: User ID
        preference: Token preference ('short', 'default', 'extended', 'long', 'very-long')
    """
    valid_preferences = ["short", "default", "extended", "long", "very-long"]
    if preference not in valid_preferences:
        raise HTTPException(status_code=400, detail=f"Invalid preference. Must be one of: {', '.join(valid_preferences)}")
    
    # Update user's preference
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"token_preference": preference}}
    )
    
    return {"message": "Token preference updated successfully"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current authenticated user from token
    
    Args:
        token: JWT token
    
    Returns:
        dict: User object
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