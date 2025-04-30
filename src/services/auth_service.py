from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId

from src.config.database import users_collection, db
from src.schemas.schemas import UserCreate, UserResponse
from config import config

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

# Password handling
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# User operations
async def create_user(user_data: UserCreate):
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

async def authenticate_user(email: str, password: str):
    user = await users_collection.find_one({"email": email})
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    
    # Convert ObjectId to string
    user["id"] = str(user["_id"])
    
    return user

# Enhanced JWT token operations
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, user_preference: Optional[str] = None):
    """
    Create a JWT token with expiration based on user preferences or default settings
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional explicit expiration time
        user_preference: Optional user preference for token expiration ('short', 'default', 'extended')
    
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    # Determine expiration time based on user preference
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default expiration from config
        default_expires = config.ACCESS_TOKEN_EXPIRE_MINUTES
        
        # Apply user preference if provided
        if user_preference == "short":
            # Short session (15 min)
            expire = datetime.utcnow() + timedelta(minutes=15)
        elif user_preference == "extended":
            # Extended session (1 day)
            expire = datetime.utcnow() + timedelta(days=1)
        elif user_preference == "long":
            # Long session (7 days)
            expire = datetime.utcnow() + timedelta(days=7)
        elif user_preference == "very-long":
            # Very long session (1 year)
            expire = datetime.utcnow() + timedelta(days=365)
        else:
            # Default session length from config
            expire = datetime.utcnow() + timedelta(minutes=default_expires)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    
    return encoded_jwt

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