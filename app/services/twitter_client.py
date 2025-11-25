"""
Twitter API client for fetching user timeline
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.core.encryption import decrypt_data


class TwitterClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.twitter.com/2"
    
    async def get_user_timeline(
        self,
        user_id: Optional[str] = None,
        max_results: int = 100,
        since_id: Optional[str] = None,
        start_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get user timeline tweets"""
        if not user_id:
            # Get authenticated user's ID first
            user_info = await self.get_me()
            user_id = user_info.get("data", {}).get("id")
        
        url = f"{self.base_url}/users/{user_id}/tweets"
        params = {
            "max_results": min(max_results, 100),  # Twitter API limit
            "tweet.fields": "created_at,author_id,public_metrics,text,lang",
            "expansions": "author_id",
            "user.fields": "name,username"
        }
        
        if since_id:
            params["since_id"] = since_id
        
        if start_time:
            params["start_time"] = start_time.isoformat()
        
        all_tweets = []
        next_token = None
        
        async with httpx.AsyncClient() as client:
            while len(all_tweets) < max_results:
                if next_token:
                    params["pagination_token"] = next_token
                
                response = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                response.raise_for_status()
                data = response.json()
                
                tweets = data.get("data", [])
                all_tweets.extend(tweets)
                
                meta = data.get("meta", {})
                next_token = meta.get("next_token")
                
                if not next_token:
                    break
        
        return all_tweets[:max_results]
    
    async def get_me(self) -> Dict:
        """Get authenticated user information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/me",
                params={"user.fields": "name,username"},
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_following_timeline(
        self,
        max_results: int = 100,
        since_id: Optional[str] = None
    ) -> List[Dict]:
        """Get timeline from users you follow"""
        url = f"{self.base_url}/tweets/search/recent"
        params = {
            "query": "from:follows",  # This requires different endpoint
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,author_id,public_metrics,text,lang"
        }
        
        # Note: Getting following timeline requires different approach
        # For now, we'll use user's own timeline
        # This can be enhanced with Twitter API v2 timeline endpoint when available
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            response.raise_for_status()
            return response.json().get("data", [])

