import asyncio
from typing import List, Dict, Any
from core.utils.bot_logger import get_logger

logger = get_logger("notification_batcher")

class NotificationBatcher:
    """
    Batches multiple notifications into a single message to reduce user interruption.
    """
    def __init__(self, window_seconds: int = 300):
        self.queue: List[Dict[str, Any]] = []
        self.window = window_seconds
        self.last_flush = 0
        self.lock = asyncio.Lock()

    async def add(self, notification: Dict[str, Any]):
        async with self.lock:
            self.queue.append(notification)
            logger.info(f"Notification added to batch: {notification.get('title', 'Untitled')}")

    async def flush(self):
        async with self.lock:
            if not self.queue:
                return None
            
            # Group by category
            groups = {}
            for item in self.queue:
                cat = item.get("category", "General")
                if cat not in groups:
                    groups[cat] = []
                groups[cat].append(item.get("content", ""))

            # Compose unified message
            sections = []
            for cat, contents in groups.items():
                sections.append(f"🔔 *{cat.upper()}*\n" + "\n".join([f"• {c}" for c in contents]))
            
            unified_msg = "☀️ *DAILY BRIEFING UPDATE*\n\n" + "\n\n".join(sections)
            self.queue.clear()
            return unified_msg

# Global instance
notification_batcher = NotificationBatcher()
