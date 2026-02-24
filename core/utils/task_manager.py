import sqlite3
import os
import re
from datetime import datetime, timedelta

class TaskManager:
    """Manages simple to-do tasks for the Telegram bot user."""
    
    def __init__(self, db_path="tasks.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
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

    def add_task(self, user_id: str, description: str) -> int:
        clean_desc, scheduled_time = self._parse_time_from_desc(description)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (user_id, description, status, scheduled_time, is_notified)
                VALUES (?, ?, 'pending', ?, 0)
            ''', (user_id, clean_desc, scheduled_time))
            conn.commit()
            return cursor.lastrowid

    def get_pending_tasks(self, user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, description, created_at, scheduled_time
                FROM tasks 
                WHERE user_id = ? AND status = 'pending'
                ORDER BY CASE WHEN scheduled_time IS NULL THEN 1 ELSE 0 END, scheduled_time ASC, created_at ASC
            ''', (user_id,))
            return [{"id": row[0], "desc": row[1], "created_at": row[2], "scheduled_time": row[3]} for row in cursor.fetchall()]

    def get_completed_tasks_today(self, user_id: str):
        today = datetime.now().strftime('%Y-%m-%d')
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, description, completed_at 
                FROM tasks 
                WHERE user_id = ? AND status = 'completed' AND date(completed_at) = ?
                ORDER BY completed_at DESC
            ''', (user_id, today))
            return [{"id": row[0], "desc": row[1], "completed_at": row[2]} for row in cursor.fetchall()]

    def complete_task(self, user_id: str, task_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND status = 'pending'
            ''', (task_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_due_tasks(self, user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, description, scheduled_time 
                FROM tasks 
                WHERE user_id = ? AND status = 'pending' AND is_notified = 0
                AND scheduled_time IS NOT NULL AND scheduled_time <= CURRENT_TIMESTAMP
            ''', (user_id,))
            tasks = [{"id": row[0], "desc": row[1], "scheduled_time": row[2]} for row in cursor.fetchall()]
            
            # Mark as notified right away to prevent duplicate triggers
            if tasks:
                task_ids = [str(t["id"]) for t in tasks]
                placeholders = ','.join('?' * len(task_ids))
                cursor.execute(f'''
                    UPDATE tasks SET is_notified = 1 
                    WHERE id IN ({placeholders}) AND user_id = ?
                ''', (*task_ids, user_id))
                conn.commit()
            
            return tasks

task_manager = TaskManager()
