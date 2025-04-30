import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # API settings
    API_VERSION = "1.0.0"
    API_TITLE = "UQIFeed API"
    API_DESCRIPTION = "API for UQIFeed - a personalized nutrition tracking application"
    
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # Database settings - MongoDB
    # Sử dụng MongoDB cục bộ nếu không thể kết nối đến Atlas
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("DB_NAME", "uqifeed_db")
    
    # JWT Authentication settings
    SECRET_KEY = os.getenv("SECRET_KEY", "YOUR_SECRET_KEY_HERE")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Google API settings
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    
    # Storage settings
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    
    # CORS settings
    CORS_ORIGINS = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

# Create instance for importing in other modules
config = Config()

