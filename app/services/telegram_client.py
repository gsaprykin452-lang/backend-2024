"""
Telegram Bot API client for fetching messages
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime
from app.core.encryption import decrypt_data


class TelegramClient:
    """Client for Telegram Bot API"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def get_me(self) -> Dict:
        """Get bot information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/getMe")
            response.raise_for_status()
            return response.json()
    
    async def get_updates(
        self,
        offset: Optional[int] = None,
        limit: int = 100,
        timeout: int = 0
    ) -> List[Dict]:
        """Get updates (messages) from Telegram"""
        params = {
            "limit": min(limit, 100),
            "timeout": timeout
        }
        if offset:
            params["offset"] = offset
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/getUpdates",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return data.get("result", [])
    
    async def get_chat(self, chat_id: str) -> Dict:
        """Get chat information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/getChat",
                params={"chat_id": chat_id}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_chat_members_count(self, chat_id: str) -> int:
        """Get number of members in chat"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/getChatMembersCount",
                params={"chat_id": chat_id}
            )
            response.raise_for_status()
            return response.json().get("result", 0)


class TelegramUserClient:
    """Client for Telegram User API (MTProto) - requires user credentials"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str):
        # Note: This requires telethon or pyrogram library
        # For MVP, we'll use Bot API which is simpler
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
    
    async def get_dialogs(self) -> List[Dict]:
        """Get user dialogs (requires MTProto client)"""
        # This would require telethon or pyrogram
        # For now, return empty list
        return []

