import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from json import JSONDecodeError

from src.config.database import users_collection
from src.services.authentication.password_manager import get_password_hash
from src.services.authentication.jwt_handler import create_access_token
from src.services.user.profile_manager import update_profile_field
import config

# Social authentication providers
PROVIDERS = {
    'google': {
        'client_id': getattr(config, 'GOOGLE_CLIENT_ID', None),
        'client_secret': getattr(config, 'GOOGLE_CLIENT_SECRET', None),
        'redirect_uri': getattr(config, 'GOOGLE_REDIRECT_URI', None),
        'discovery_url': 'https://accounts.google.com/.well-known/openid-configuration',
    },
    'facebook': {
        'client_id': getattr(config, 'FACEBOOK_CLIENT_ID', None),
        'client_secret': getattr(config, 'FACEBOOK_CLIENT_SECRET', None),
        'redirect_uri': getattr(config, 'FACEBOOK_REDIRECT_URI', None),
        'token_url': 'https://graph.facebook.com/v13.0/oauth/access_token',
        'user_info_url': 'https://graph.facebook.com/me?fields=id,name,email,picture',
    }
}

async def verify_google_token(token: str) -> Dict[str, Any]:
    """
    Verify Google ID token and extract user info
    
    Args:
        token: Google ID token
    
    Returns:
        Dict: User information from Google
    """
    try:
        # Verify the token
        client_id = PROVIDERS['google']['client_id']
        if not client_id:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            client_id
        )
        
        # Check if the token is valid
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        
        # Get user info
        user_info = {
            'provider': 'google',
            'provider_user_id': idinfo['sub'],
            'email': idinfo.get('email'),
            'name': idinfo.get('name'),
            'picture': idinfo.get('picture')
        }
        
        return user_info
    
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying Google token: {str(e)}")

async def get_facebook_user_info(access_token: str) -> Dict[str, Any]:
    """
    Get user info from Facebook using access token
    
    Args:
        access_token: Facebook access token
    
    Returns:
        Dict: User information from Facebook
    """
    try:
        # Get user info from Facebook Graph API
        user_info_url = PROVIDERS['facebook']['user_info_url']
        
        response = requests.get(
            user_info_url,
            params={'access_token': access_token}
        )
        response.raise_for_status()
        
        fb_user = response.json()
        
        user_info = {
            'provider': 'facebook',
            'provider_user_id': fb_user['id'],
            'email': fb_user.get('email'),
            'name': fb_user.get('name'),
            'picture': fb_user.get('picture', {}).get('data', {}).get('url')
        }
        
        return user_info
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Facebook API error: {str(e)}")
    except JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid response from Facebook")
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"Missing field in Facebook response: {str(e)}")

async def authenticate_social_user(user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Authenticate or create a user from social login info
    
    Args:
        user_info: User information from social provider
    
    Returns:
        Dict: Authenticated user info with access token
    """
    try:
        provider = user_info['provider']
        provider_user_id = user_info['provider_user_id']
        email = user_info.get('email')
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by social provider")
        
        # Check if user exists by provider ID
        user = await users_collection.find_one({
            f"{provider}_id": provider_user_id
        })
        
        if not user:
            # Check if user exists by email
            user = await users_collection.find_one({
                "email": email
            })
            
            if user:
                # Update user with provider ID
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {
                        f"{provider}_id": provider_user_id,
                        "updated_at": datetime.utcnow()
                    }}
                )
            else:
                # Create a new user
                new_user = {
                    "email": email,
                    "name": user_info.get('name', email.split('@')[0]),
                    "password": get_password_hash(os.urandom(24).hex()),  # Random secure password
                    f"{provider}_id": provider_user_id,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                result = await users_collection.insert_one(new_user)
                user_id = str(result.inserted_id)
                
                # Create initial profile
                await update_profile_field(
                    user_id=user_id,
                    field="picture",
                    value=user_info.get('picture')
                )
                
                # Retrieve the newly created user
                user = await users_collection.find_one({"_id": result.inserted_id})
        
        # Create access token
        user_data = {
            "sub": user["email"],
            "id": str(user["_id"]),
            "name": user.get("name", "")
        }
        
        access_token = create_access_token(data=user_data)
        
        # Clean up user object for response
        if "_id" in user:
            user["id"] = str(user["_id"])
            del user["_id"]
        
        if "password" in user:
            del user["password"]
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

async def exchange_oauth_code(provider: str, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """
    Exchange OAuth authorization code for access token
    
    Args:
        provider: OAuth provider (google, facebook)
        code: Authorization code
        redirect_uri: Redirect URI (optional)
    
    Returns:
        Dict: Access token response
    """
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    
    provider_config = PROVIDERS[provider]
    
    if not provider_config['client_id'] or not provider_config['client_secret']:
        raise HTTPException(status_code=500, detail=f"{provider.capitalize()} OAuth not configured")
    
    try:
        if provider == 'google':
            # Exchange code for Google token
            token_url = "https://oauth2.googleapis.com/token"
            
            data = {
                'code': code,
                'client_id': provider_config['client_id'],
                'client_secret': provider_config['client_secret'],
                'redirect_uri': redirect_uri or provider_config['redirect_uri'],
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Verify ID token and get user info
            user_info = await verify_google_token(token_data['id_token'])
            
            return await authenticate_social_user(user_info)
            
        elif provider == 'facebook':
            # Exchange code for Facebook token
            token_url = provider_config['token_url']
            
            params = {
                'client_id': provider_config['client_id'],
                'client_secret': provider_config['client_secret'],
                'redirect_uri': redirect_uri or provider_config['redirect_uri'],
                'code': code
            }
            
            response = requests.get(token_url, params=params)
            response.raise_for_status()
            token_data = response.json()
            
            # Get user info with access token
            user_info = await get_facebook_user_info(token_data['access_token'])
            
            return await authenticate_social_user(user_info)
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error exchanging code: {str(e)}")
    except JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid response from OAuth provider")