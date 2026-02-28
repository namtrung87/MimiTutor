"""
ConversationStore: SQLite-based persistent conversation memory.

Replaces the in-memory approach so conversations survive bot restarts.
Provides token-aware context retrieval and automatic pruning.
"""
import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core.utils.db_utils import AsyncSQLite


class ConversationStore:
    """Persistent conversation memory using SQLite."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            data_dir = os.path.join(root_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "conversations.db")

        self.db_path = db_path
        self.db = AsyncSQLite(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    routing_category TEXT,
                    response_time_ms INTEGER,
                    timestamp TEXT DEFAULT (datetime('now', 'localtime'))
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_user_ts 
                ON messages(user_id, timestamp DESC)
            ''')
            conn.commit()

    async def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        routing_category: str = None,
        response_time_ms: int = None,
    ):
        """Add a message to the conversation history."""
        query = '''INSERT INTO messages (user_id, role, content, routing_category, response_time_ms)
                   VALUES (?, ?, ?, ?, ?)'''
        params = (user_id, role, content, routing_category, response_time_ms)
        await self.db.execute(query, params)

    async def get_context(
        self,
        user_id: str,
        max_messages: int = 10,
        max_chars: int = 4000,
    ) -> List[Dict]:
        """
        Retrieve recent conversation context, respecting token limits.
        Returns messages newest-first, reversed to chronological order.
        """
        query = '''SELECT role, content, routing_category, timestamp
                   FROM messages
                   WHERE user_id = ?
                   ORDER BY timestamp DESC
                   LIMIT ?'''
        params = (user_id, max_messages * 2)
        rows = await self.db.fetch_all(query, params)

        # Trim to max_chars (approximate token control)
        result = []
        total_chars = 0
        for row in rows:
            content_len = len(row["content"])
            if total_chars + content_len > max_chars:
                break
            result.append(row)
            total_chars += content_len

        # Return in chronological order (oldest first)
        result.reverse()
        return result[:max_messages]

    async def get_context_string(self, user_id: str, max_chars: int = 3000) -> str:
        """Get conversation context as a formatted string for LLM prompts."""
        messages = await self.get_context(user_id, max_chars=max_chars)
        if not messages:
            return ""

        lines = []
        for m in messages:
            role_label = "User" if m["role"] == "user" else "Bot"
            lines.append(f"[{role_label}]: {m['content']}")
        return "\n".join(lines)

    async def get_last_routing(self, user_id: str, n: int = 3) -> List[str]:
        """Get the last N routing categories for routing history context."""
        query = '''SELECT DISTINCT routing_category
                   FROM messages
                   WHERE user_id = ? AND routing_category IS NOT NULL
                   ORDER BY timestamp DESC
                   LIMIT ?'''
        params = (user_id, n)
        rows = await self.db.fetch_all(query, params)
        return [row["routing_category"] for row in rows]

    async def get_stats(self, user_id: str) -> Dict:
        """Get conversation statistics for /metrics."""
        # Total messages
        total_row = await self.db.fetch_one(
            "SELECT COUNT(*) as cnt FROM messages WHERE user_id = ?", (user_id,)
        )
        total = total_row["cnt"] if total_row else 0

        # Today's messages
        today = datetime.now().strftime("%Y-%m-%d")
        today_row = await self.db.fetch_one(
            "SELECT COUNT(*) as cnt FROM messages WHERE user_id = ? AND date(timestamp) = ?",
            (user_id, today),
        )
        today_count = today_row["cnt"] if today_row else 0

        # Routing distribution (today)
        routing = await self.db.fetch_all(
            '''SELECT routing_category, COUNT(*) as cnt
               FROM messages
               WHERE user_id = ? AND date(timestamp) = ? AND routing_category IS NOT NULL
               GROUP BY routing_category
               ORDER BY cnt DESC''',
            (user_id, today),
        )

        # Average response time (today)
        avg_row = await self.db.fetch_one(
            '''SELECT AVG(response_time_ms) as avg_ms
               FROM messages
               WHERE user_id = ? AND date(timestamp) = ? AND response_time_ms IS NOT NULL''',
            (user_id, today),
        )
        avg_rt = avg_row["avg_ms"] if avg_row else None

        return {
            "total_messages": total,
            "today_messages": today_count,
            "routing_distribution": {r["routing_category"]: r["cnt"] for r in routing},
            "avg_response_time_ms": round(avg_rt) if avg_rt else None,
        }

    async def prune_old(self, days: int = 7):
        """Delete messages older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        # We can use execute for deletion
        # But we want the rowcount, AsyncSQLite.execute doesn't return it currently
        # I'll update AsyncSQLite or just use run_in_transaction
        async def _prune(conn):
            return conn.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,)).rowcount
        
        deleted = await self.db.run_in_transaction(_prune)
        if deleted:
             # We should use logger here too
             from core.utils.bot_logger import get_logger
             logger = get_logger("conversation_store")
             logger.info(f"Pruned {deleted} messages older than {days} days")
        return deleted

    async def clear_user(self, user_id: str):
        """Clear all conversation history for a user."""
        await self.db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))


# Global instance
conversation_store = ConversationStore()
