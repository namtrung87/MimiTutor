import os
import asyncio
from typing import Optional, Any
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

class TelegramService:
    """
    Service responsible for handling external communications via Telegram.
    Provides both asynchronous and fallback synchronous methods to ensure message delivery.
    """
    def __init__(self) -> None:
        """Initializes the Telegram bot client using environment variables."""
        self.token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.user_id: Optional[str] = os.getenv("TELEGRAM_USER_ID")
        if not self.token or not self.user_id:
            print("Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID not found in .env")
        self.bot: Optional[Bot] = Bot(token=self.token) if self.token else None

    def send_message_sync(self, text: str, parse_mode: Optional[str] = "Markdown") -> bool:
        """
        Failsafe synchronous message sending using the requests library.
        
        Args:
            text (str): The content of the message to send.
            parse_mode (Optional[str]): Formatting mode (e.g., 'Markdown'). Defaults to 'Markdown'.
            
        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        if not self.token or not self.user_id:
            return False
        
        import requests
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self.user_id,
            "text": text,
            "parse_mode": parse_mode
        }
        try:
            r = requests.post(url, data=payload, timeout=10)
            if r.status_code == 200:
                return True
            # Retry without markdown if it failed
            if parse_mode:
                payload["parse_mode"] = None
                r = requests.post(url, data=payload, timeout=10)
                return r.status_code == 200
            return False
        except Exception as e:
            print(f"  [TelegramService] Sync fallback failed: {e}")
            return False

    async def send_message(self, text: str, reply_markup: Optional[Any] = None, parse_mode: Optional[str] = "Markdown") -> bool:
        """
        Sends a message asynchronously, with a synchronous fallback on failure.
        
        Args:
            text (str): The content of the message to send.
            reply_markup (Optional[Any]): Inline keyboard or reply markup. Defaults to None.
            parse_mode (Optional[str]): Formatting mode. Defaults to 'Markdown'.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.token or not self.user_id:
            print(f"Telegram not configured. Message: {text}")
            return False
        
        # 1. Primary Attempt: Async
        try:
            # We wrap in a timeout to prevent hanging the whole worker
            await asyncio.wait_for(
                self.bot.send_message(
                    chat_id=self.user_id, 
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                ),
                timeout=8
            )
            return True
        except Exception as e:
            print(f"  [TelegramService] Async send error: {e}. Trying sync fallback...")
            # 2. Fallback Attempt: Sync
            return self.send_message_sync(text, parse_mode)

    async def send_photo(self, photo_path: str, caption: Optional[str] = None, reply_markup: Optional[Any] = None) -> bool:
        """
        Sends a photo to the configured Telegram user ID.
        
        Args:
            photo_path (str): The absolute file path to the photo.
            caption (Optional[str]): Optional caption for the photo. Defaults to None.
            reply_markup (Optional[Any]): Optional inline keyboard. Defaults to None.
            
        Returns:
            bool: True if the photo was sent successfully, False otherwise.
        """
        if not self.bot or not self.user_id:
            return False
        
        try:
            with open(photo_path, 'rb') as photo:
                await self.bot.send_photo(
                    chat_id=self.user_id, 
                    photo=photo,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            return True
        except Exception as e:
            print(f"Error sending Telegram photo: {e}")
            # Simplified sync fallback for photos could be added if needed
            return False

# Global instance
telegram_service = TelegramService()

if __name__ == "__main__":
    # Test script
    async def main():
        success = await telegram_service.send_message("🚀 Orchestra Assistant: Telegram Service is online!")
        print(f"Test message sent: {success}")

    if telegram_service.token:
        asyncio.run(main())
