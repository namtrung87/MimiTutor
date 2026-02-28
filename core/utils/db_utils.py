import sqlite3
import asyncio
from typing import Any, List, Dict, Optional, Callable

class AsyncSQLite:
    """
    Utility class to wrap synchronous sqlite3 calls in asyncio.to_thread
    to avoid blocking the event loop.
    Includes WAL mode for better concurrency.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._set_wal_mode()

    def _set_wal_mode(self):
        """Enable Write-Ahead Logging for better concurrent access."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.commit()
        except Exception:
            pass

    async def execute(self, query: str, params: tuple = ()) -> None:
        def _exec():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL") # Ensure it's set for this connection
                conn.execute(query, params)
                conn.commit()
        await asyncio.to_thread(_exec)

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        def _fetch():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        return await asyncio.to_thread(_fetch)

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        def _fetch():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        return await asyncio.to_thread(_fetch)

    async def run_in_transaction(self, callback: Callable[[sqlite3.Connection], Any]) -> Any:
        def _run():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                result = callback(conn)
                conn.commit()
                return result
        return await asyncio.to_thread(_run)
