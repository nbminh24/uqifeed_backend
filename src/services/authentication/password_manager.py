from passlib.context import CryptContext
from src.config.database import users_collection
from src.utils.db_utils import safe_db_operation
import re
from datetime import datetime, timedelta
import secrets
import string
from typing import Dict, Any, Tuple
from fastapi import HTTPException
from src.config.constants import ERROR_MESSAGES
from src.utils.validation import validate_password_strength, validate_email
from src.utils.rate_limiter import rate_limiter

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password strength requirements
PASSWORD_REQUIREMENTS = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special": True
}

# Rate limiting settings
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT_MINUTES = 15

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength against requirements
    
    Args:
        password: Password to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < PASSWORD_REQUIREMENTS["min_length"]:
        return False, f"Password must be at least {PASSWORD_REQUIREMENTS['min_length']} characters long"
    
    if PASSWORD_REQUIREMENTS["require_uppercase"] and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if PASSWORD_REQUIREMENTS["require_lowercase"] and not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if PASSWORD_REQUIREMENTS["require_digit"] and not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if PASSWORD_REQUIREMENTS["require_special"] and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, ""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)

def generate_reset_token() -> str:
    """
    Generate a secure random token for password reset
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

async def authenticate_user(email: str, password: str) -> Tuple[bool, str]:
    """
    Authenticate a user with email and password
    
    Args:
        email: User's email
        password: User's password
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Validate email format
        is_valid, error_msg = validate_email(email)
        if not is_valid:
            return False, error_msg
        
        # Check rate limit
        await rate_limiter.check_rate_limit(email)
        
        # Get user from database
        user = await safe_db_operation(
            users_collection.find_one({"email": email})
        )
        if not user:
            return False, ERROR_MESSAGES["invalid_credentials"]
        
        # Verify password
        if not await verify_password(password, user["password"]):
            return False, ERROR_MESSAGES["invalid_credentials"]
        
        # Reset rate limit on successful login
        rate_limiter.reset_attempts(email)
        
        # Convert ObjectId to string
        user["id"] = str(user["_id"])
        return True, "Authentication successful"
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES["db_operation_failed"].format(error=str(e))
        )

async def initiate_password_reset(email: str) -> tuple[bool, str]:
    """
    Initiate password reset process
    """
    user = await safe_db_operation(
        users_collection.find_one({"email": email})
    )
    
    if not user:
        return False, "User not found"
    
    reset_token = generate_reset_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    await safe_db_operation(
        users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "reset_token": reset_token,
                    "reset_token_expires": expires_at
                }
            }
        )
    )
    
    return True, reset_token

async def reset_password(reset_token: str, new_password: str) -> tuple[bool, str]:
    """
    Reset password using reset token
    """
    # Validate password strength
    is_valid, error_message = validate_password_strength(new_password)
    if not is_valid:
        return False, error_message
    
    user = await safe_db_operation(
        users_collection.find_one({
            "reset_token": reset_token,
            "reset_token_expires": {"$gt": datetime.utcnow()}
        })
    )
    
    if not user:
        return False, "Invalid or expired reset token"
    
    # Update password and clear reset token
    await safe_db_operation(
        users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {"password": get_password_hash(new_password)},
                "$unset": {"reset_token": "", "reset_token_expires": ""}
            }
        )
    )
    
    return True, "Password reset successful"

async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user
    
    Args:
        user_data: User data including email and password
        
    Returns:
        Created user data
    """
    try:
        # Validate email
        is_valid, error_msg = validate_email(user_data["email"])
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(user_data["password"])
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Check if user exists
        existing_user = await safe_db_operation(
            users_collection.find_one({"email": user_data["email"]})
        )
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
        
        # Hash password
        hashed_password = get_password_hash(user_data["password"])
        
        # Create user document
        user_doc = {
            "email": user_data["email"],
            "password": hashed_password,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "is_verified": False
        }
        
        # Insert user
        result = await safe_db_operation(
            users_collection.insert_one(user_doc)
        )
        user_doc["_id"] = result.inserted_id
        
        return user_doc
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES["db_operation_failed"].format(error=str(e))
        )