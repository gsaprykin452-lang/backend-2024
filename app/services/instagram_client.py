"""
Instagram Basic Display API client for fetching media
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime
from app.core.encryption import decrypt_data


class InstagramClient:
    """Client for Instagram Basic Display API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.instagram.com"
    
    async def get_user_media(
        self,
        user_id: str = "me",
        limit: int = 100,
        after: Optional[str] = None
    ) -> List[Dict]:
        """Get user's media (photos and videos)"""
        params = {
            "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username",
            "access_token": self.access_token,
            "limit": min(limit, 100)
        }
        
        if after:
            params["after"] = after
        
        all_media = []
        next_cursor = None
        
        async with httpx.AsyncClient() as client:
            while len(all_media) < limit:
                if next_cursor:
                    params["after"] = next_cursor
                
                response = await client.get(
                    f"{self.base_url}/{user_id}/media",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                media_items = data.get("data", [])
                all_media.extend(media_items)
                
                paging = data.get("paging", {})
                cursors = paging.get("cursors", {})
                next_cursor = cursors.get("after")
                
                if not next_cursor:
                    break
        
        return all_media[:limit]
    
    async def get_media_details(self, media_id: str) -> Dict:
        """Get details of a specific media item"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{media_id}",
                params={
                    "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username,like_count,comments_count",
                    "access_token": self.access_token
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_me(self) -> Dict:
        """Get authenticated user information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me",
                params={
                    "fields": "id,username",
                    "access_token": self.access_token
                }
            )
            response.raise_for_status()
            return response.json()

