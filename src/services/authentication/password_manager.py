from passlib.context import CryptContext
from src.config.database import users_collection

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """
    Verify a plain password against a hashed password
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
    
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """
    Create a password hash
    
    Args:
        password: Plain text password to hash
    
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)

async def authenticate_user(email: str, password: str):
    """
    Authenticate a user with email and password
    
    Args:
        email: User's email
        password: User's plain text password
    
    Returns:
        dict: User object if authentication successful, False otherwise
    """
    user = await users_collection.find_one({"email": email})
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    
    # Convert ObjectId to string
    user["id"] = str(user["_id"])
    
    return user