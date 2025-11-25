"""
Instagram Basic Display API OAuth integration
"""
import httpx
from typing import Optional, Dict
from app.core.config import settings

# Instagram OAuth endpoints
INSTAGRAM_AUTHORIZE_URL = "https://api.instagram.com/oauth/authorize"
INSTAGRAM_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
INSTAGRAM_API_BASE = "https://graph.instagram.com"


class InstagramOAuth:
    def __init__(self, app_id: str, app_secret: str, redirect_uri: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self, state: str) -> str:
        """Generate Instagram OAuth authorization URL"""
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user_profile,user_media",
            "response_type": "code",
            "state": state
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{INSTAGRAM_AUTHORIZE_URL}?{query_string}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access token"""
        data = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code": code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                INSTAGRAM_TOKEN_URL,
                data=data
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, access_token: str) -> Dict:
        """Refresh long-lived access token"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{INSTAGRAM_API_BASE}/refresh_access_token",
                params={
                    "grant_type": "ig_refresh_token",
                    "access_token": access_token
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict:
        """Get authenticated user information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{INSTAGRAM_API_BASE}/me",
                params={
                    "fields": "id,username",
                    "access_token": access_token
                }
            )
            response.raise_for_status()
            return response.json()

