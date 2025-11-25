"""
Facebook Graph API client for fetching posts
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.core.encryption import decrypt_data


class FacebookClient:
    """Client for Facebook Graph API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"
    
    async def get_user_feed(
        self,
        user_id: str = "me",
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """Get user's feed/posts"""
        params = {
            "access_token": self.access_token,
            "fields": "id,message,created_time,from,likes.summary(true),comments.summary(true),shares",
            "limit": min(limit, 100)
        }
        
        if since:
            params["since"] = int(since.timestamp())
        
        all_posts = []
        next_url = f"{self.base_url}/{user_id}/feed"
        
        async with httpx.AsyncClient() as client:
            while len(all_posts) < limit:
                response = await client.get(next_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                posts = data.get("data", [])
                all_posts.extend(posts)
                
                paging = data.get("paging", {})
                next_url = paging.get("next")
                
                if not next_url:
                    break
                
                # Remove access_token from next_url and add it as param
                params = {"access_token": self.access_token}
        
        return all_posts[:limit]
    
    async def get_page_posts(
        self,
        page_id: str,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """Get posts from a Facebook page"""
        params = {
            "access_token": self.access_token,
            "fields": "id,message,created_time,from,likes.summary(true),comments.summary(true),shares",
            "limit": min(limit, 100)
        }
        
        if since:
            params["since"] = int(since.timestamp())
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{page_id}/posts",
                params=params
            )
            response.raise_for_status()
            return response.json().get("data", [])
    
    async def get_me(self) -> Dict:
        """Get authenticated user information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me",
                params={
                    "access_token": self.access_token,
                    "fields": "id,name,email"
                }
            )
            response.raise_for_status()
            return response.json()

