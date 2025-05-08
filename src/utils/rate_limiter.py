from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException
from src.config.constants import MAX_LOGIN_ATTEMPTS, LOGIN_TIMEOUT_MINUTES, ERROR_MESSAGES

class RateLimiter:
    def __init__(self):
        self._attempts: Dict[str, Dict[str, int]] = {}  # {user_id: {attempts: count, last_attempt: timestamp}}
    
    async def check_rate_limit(self, user_id: str) -> None:
        """
        Check if user has exceeded rate limit
        
        Args:
            user_id: User ID to check
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        current_time = datetime.utcnow()
        
        # Get user's attempt data
        user_data = self._attempts.get(user_id, {"attempts": 0, "last_attempt": current_time})
        
        # Check if timeout period has passed
        if (current_time - user_data["last_attempt"]) > timedelta(minutes=LOGIN_TIMEOUT_MINUTES):
            # Reset attempts if timeout has passed
            user_data = {"attempts": 0, "last_attempt": current_time}
        
        # Check if max attempts reached
        if user_data["attempts"] >= MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail=ERROR_MESSAGES["rate_limit_exceeded"]
            )
        
        # Update attempt data
        user_data["attempts"] += 1
        user_data["last_attempt"] = current_time
        self._attempts[user_id] = user_data
    
    def reset_attempts(self, user_id: str) -> None:
        """
        Reset rate limit attempts for a user
        
        Args:
            user_id: User ID to reset
        """
        if user_id in self._attempts:
            del self._attempts[user_id]
    
    def get_remaining_attempts(self, user_id: str) -> Optional[int]:
        """
        Get remaining attempts for a user
        
        Args:
            user_id: User ID to check
            
        Returns:
            Number of remaining attempts or None if no attempts recorded
        """
        if user_id not in self._attempts:
            return None
        
        user_data = self._attempts[user_id]
        if (datetime.utcnow() - user_data["last_attempt"]) > timedelta(minutes=LOGIN_TIMEOUT_MINUTES):
            return MAX_LOGIN_ATTEMPTS
        
        return max(0, MAX_LOGIN_ATTEMPTS - user_data["attempts"])

# Create global rate limiter instance
rate_limiter = RateLimiter() 