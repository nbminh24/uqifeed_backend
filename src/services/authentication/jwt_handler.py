from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Tuple
import config
from src.utils.db_utils import safe_db_operation
from src.config.database import db

# Collections for token management
blacklisted_tokens = db.blacklisted_tokens
refresh_tokens = db.refresh_tokens

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, user_preference: Optional[str] = None) -> str:
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

async def create_refresh_token(user_id: str) -> str:
    """
    Create a refresh token for a user
    """
    refresh_token = jwt.encode(
        {"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=30)},
        config.REFRESH_TOKEN_SECRET,
        algorithm=config.ALGORITHM
    )
    
    # Store refresh token in database
    await safe_db_operation(
        refresh_tokens.insert_one({
            "user_id": user_id,
            "token": refresh_token,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30)
        })
    )
    
    return refresh_token

async def verify_token(token: str) -> Tuple[bool, dict]:
    """
    Verify a JWT token and check if it's blacklisted
    """
    try:
        # Check if token is blacklisted
        is_blacklisted = await safe_db_operation(
            blacklisted_tokens.find_one({"token": token})
        )
        if is_blacklisted:
            return False, {"error": "Token has been revoked"}
        
        # Verify token
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return True, payload
    except JWTError:
        return False, {"error": "Invalid token"}

async def blacklist_token(token: str) -> bool:
    """
    Add a token to the blacklist
    """
    try:
        # Decode token to get expiration
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        expires_at = datetime.fromtimestamp(payload["exp"])
        
        # Add to blacklist
        await safe_db_operation(
            blacklisted_tokens.insert_one({
                "token": token,
                "blacklisted_at": datetime.utcnow(),
                "expires_at": expires_at
            })
        )
        return True
    except JWTError:
        return False

async def refresh_access_token(refresh_token: str) -> Optional[str]:
    """
    Create a new access token using a refresh token
    """
    try:
        # Verify refresh token
        payload = jwt.decode(refresh_token, config.REFRESH_TOKEN_SECRET, algorithms=[config.ALGORITHM])
        user_id = payload["user_id"]
        
        # Check if refresh token exists in database
        token_exists = await safe_db_operation(
            refresh_tokens.find_one({
                "user_id": user_id,
                "token": refresh_token,
                "expires_at": {"$gt": datetime.utcnow()}
            })
        )
        
        if not token_exists:
            return None
        
        # Create new access token
        return create_access_token({"sub": user_id})
    except JWTError:
        return None