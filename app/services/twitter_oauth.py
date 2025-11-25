"""
Twitter OAuth 2.0 integration
"""
import httpx
from typing import Optional, Dict
from app.core.config import settings

# Twitter OAuth endpoints
TWITTER_AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
TWITTER_API_BASE = "https://api.twitter.com/2"


class TwitterOAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self, state: str, code_challenge: str, code_challenge_method: str = "plain") -> str:
        """Generate Twitter OAuth authorization URL"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "tweet.read users.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{TWITTER_AUTHORIZE_URL}?{query_string}"
    
    async def exchange_code_for_tokens(self, code: str, code_verifier: Optional[str] = None) -> Dict:
        """Exchange authorization code for access and refresh tokens"""
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        
        if code_verifier:
            data["code_verifier"] = code_verifier
        
        auth = (self.client_id, self.client_secret)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TWITTER_TOKEN_URL,
                data=data,
                auth=auth,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token"""
        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.client_id,
        }
        
        auth = (self.client_id, self.client_secret)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TWITTER_TOKEN_URL,
                data=data,
                auth=auth,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict:
        """Get authenticated user information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TWITTER_API_BASE}/users/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()

