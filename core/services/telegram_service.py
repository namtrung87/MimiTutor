import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

class TelegramService:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.user_id = os.getenv("TELEGRAM_USER_ID")
        if not self.token or not self.user_id:
            print("Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID not found in .env")
        self.bot = Bot(token=self.token) if self.token else None

    async def send_message(self, text: str, reply_markup=None, parse_mode="Markdown"):
        """Sends a message to the configured Telegram user ID."""
        if not self.bot or not self.user_id:
            print(f"Telegram not configured. Message: {text}")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.user_id, 
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            print(f"Error sending Telegram message (mode={parse_mode}): {e}")
            if parse_mode:
                print("Retrying without Markdown...")
                try:
                    await self.bot.send_message(
                        chat_id=self.user_id, 
                        text=text,
                        parse_mode=None,
                        reply_markup=reply_markup
                    )
                    return True
                except Exception as e2:
                    print(f"Final error sending Telegram message: {e2}")
            return False

    async def send_photo(self, photo_path: str, caption: str = None, reply_markup=None):
        """Sends a photo to the configured Telegram user ID."""
        if not self.bot or not self.user_id:
            print(f"Telegram not configured. Cannot send photo: {photo_path}")
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
