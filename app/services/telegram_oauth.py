"""
Telegram Bot setup and webhook configuration
"""
import httpx
from typing import Dict, Optional


class TelegramBotSetup:
    """Setup and manage Telegram bot"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def set_webhook(self, webhook_url: str) -> Dict:
        """Set webhook URL for receiving updates"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/setWebhook",
                json={"url": webhook_url}
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_webhook(self) -> Dict:
        """Delete webhook"""
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/deleteWebhook")
            response.raise_for_status()
            return response.json()
    
    async def get_webhook_info(self) -> Dict:
        """Get webhook information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/getWebhookInfo")
            response.raise_for_status()
            return response.json()
    
    async def create_invite_link(self, chat_id: str) -> str:
        """Create invite link for bot to join chat"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/createChatInviteLink",
                params={"chat_id": chat_id}
            )
            response.raise_for_status()
            return response.json().get("result", {}).get("invite_link", "")

