# Re-export authentication functions for backward compatibility
from src.services.authentication.user_auth import get_current_user

__all__ = [
    "get_current_user"
]