import os
import re
from datetime import datetime, timedelta
from core.utils.db_utils import AsyncSQLite

class TaskManager:
    """Manages simple to-do tasks for the Telegram bot user."""
    
    def __init__(self, db_path="tasks.db"):
        self.db_path = db_path
        self.db = AsyncSQLite(db_path)
        self._init_db()
        
    def _init_db(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            # Add new columns if missing (Schema Evolution)
            try:
                cursor.execute("ALTER TABLE tasks ADD COLUMN scheduled_time TIMESTAMP")
                cursor.execute("ALTER TABLE tasks ADD COLUMN is_notified INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass # Columns already exist
            conn.commit()

    def _parse_time_from_desc(self, description: str):
        # Match patterns like "15:30", "09:00", "8:00"
        match = re.search(r'\b(\d{1,2}):(\d{2})\b', description)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
            now = datetime.now()
            try:
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            except ValueError:
                return description, None # invalid hour/min
                
            # If time has already passed today, assume tomorrow
            if target_time < now:
                target_time += timedelta(days=1)
            
            # Clean up description
            clean_desc = description.replace(match.group(0), "").replace("lúc", "").replace("@", "").replace("vào", "").replace("  ", " ").strip()
            return clean_desc, target_time.strftime('%Y-%m-%d %H:%M:%S')
        return description, None

    async def add_task(self, user_id: str, description: str) -> int:
        clean_desc, scheduled_time = self._parse_time_from_desc(description)
        
        query = '''
            INSERT INTO tasks (user_id, description, status, scheduled_time, is_notified)
            VALUES (?, ?, 'pending', ?, 0)
        '''
        params = (user_id, clean_desc, scheduled_time)
        return await self.db.execute(query, params)

    async def get_pending_tasks(self, user_id: str):
        query = '''
            SELECT id, description, created_at, scheduled_time
            FROM tasks 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY CASE WHEN scheduled_time IS NULL THEN 1 ELSE 0 END, scheduled_time ASC, created_at ASC
        '''
        rows = await self.db.fetch_all(query, (user_id,))
        return [{"id": row["id"], "desc": row["description"], "created_at": row["created_at"], "scheduled_time": row["scheduled_time"]} for row in rows]

    async def get_completed_tasks_today(self, user_id: str):
        today = datetime.now().strftime('%Y-%m-%d')
        query = '''
            SELECT id, description, completed_at 
            FROM tasks 
            WHERE user_id = ? AND status = 'completed' AND date(completed_at) = ?
            ORDER BY completed_at DESC
        '''
        rows = await self.db.fetch_all(query, (user_id, today))
        return [{"id": row["id"], "desc": row["description"], "completed_at": row["completed_at"]} for row in rows]

    async def complete_task(self, user_id: str, task_id: int) -> bool:
        # Note: rowcount isn't returned by AsyncSQLite.execute currently
        # I'll update AsyncSQLite to return it or use fetch_one/run_in_transaction
        async def _complete(conn):
            cursor = conn.execute('''
                UPDATE tasks 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status = 'pending'
            ''', (task_id, user_id))
            return cursor.rowcount > 0
        
        return await self.db.run_in_transaction(_complete)

    async def get_due_tasks(self, user_id: str):
        query = '''
            SELECT id, description, scheduled_time 
            FROM tasks 
            WHERE user_id = ? AND status = 'pending' AND is_notified = 0
            AND scheduled_time IS NOT NULL AND scheduled_time <= CURRENT_TIMESTAMP
        '''
        rows = await self.db.fetch_all(query, (user_id,))
        tasks = [{"id": row["id"], "desc": row["description"], "scheduled_time": row["scheduled_time"]} for row in rows]
        
        # Mark as notified right away to prevent duplicate triggers
        if tasks:
            async def _mark_notified(conn):
                task_ids = [t["id"] for t in tasks]
                placeholders = ','.join('?' * len(task_ids))
                conn.execute(f'''
                    UPDATE tasks SET is_notified = 1 
                    WHERE id IN ({placeholders}) AND user_id = ?
                ''', (*task_ids, user_id))
            
            await self.db.run_in_transaction(_mark_notified)
        
        return tasks

task_manager = TaskManager()
