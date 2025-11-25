"""
Facebook OAuth 2.0 integration
"""
import httpx
from typing import Optional, Dict, List
from app.core.config import settings

# Facebook OAuth endpoints
FACEBOOK_AUTHORIZE_URL = "https://www.facebook.com/v18.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
FACEBOOK_API_BASE = "https://graph.facebook.com/v18.0"


class FacebookOAuth:
    def __init__(self, app_id: str, app_secret: str, redirect_uri: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self, state: str) -> str:
        """Generate Facebook OAuth authorization URL"""
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "pages_read_engagement,read_insights,public_profile",
            "response_type": "code"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{FACEBOOK_AUTHORIZE_URL}?{query_string}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access token"""
        params = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": self.redirect_uri,
            "code": code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                FACEBOOK_TOKEN_URL,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_long_lived_token(self, short_lived_token: str) -> Dict:
        """Exchange short-lived token for long-lived token"""
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                FACEBOOK_TOKEN_URL,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict:
        """Get authenticated user information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FACEBOOK_API_BASE}/me",
                params={
                    "access_token": access_token,
                    "fields": "id,name,email"
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_pages(self, access_token: str) -> List[Dict]:
        """Get user's Facebook pages"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FACEBOOK_API_BASE}/me/accounts",
                params={"access_token": access_token}
            )
            response.raise_for_status()
            return response.json().get("data", [])

