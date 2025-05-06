from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import config

# JWT token operations
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