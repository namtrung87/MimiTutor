import sqlite3
import os
from datetime import datetime
import json

class InteractionLogger:
    def __init__(self, db_path=None):
        if db_path is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            db_dir = os.path.join(root_dir, "data")
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
            db_path = os.path.join(db_dir, "mimi_interactions.db")
        
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_id TEXT,
                user_input TEXT,
                intent TEXT,
                agent_thought TEXT,
                agent_output TEXT,
                tags TEXT,
                metadata TEXT
            )
        ''')
        conn.commit()

        # Check for missing columns (e.g., tags)
        cursor.execute("PRAGMA table_info(interactions)")
        columns = [row[1] for row in cursor.fetchall()]
        if "tags" not in columns:
            print("  [InteractionLogger] Patching database: Adding 'tags' column...")
            cursor.execute("ALTER TABLE interactions ADD COLUMN tags TEXT")
            conn.commit()

        conn.close()

    def log_interaction(self, user_id, user_input, intent, agent_thought, agent_output, tags=None, metadata=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO interactions (timestamp, user_id, user_input, intent, agent_thought, agent_output, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            user_id,
            user_input,
            intent,
            agent_thought,
            agent_output,
            json.dumps(tags) if tags else None,
            json.dumps(metadata) if metadata else None
        ))
        conn.commit()
        conn.close()

    def get_daily_interactions(self, user_id="default_user"):
        """Retrieves all interactions for the current day."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        today_start = datetime.now().strftime("%Y-%m-%d") + "T00:00:00"
        
        cursor.execute('''
            SELECT user_input, intent, agent_output, timestamp 
            FROM interactions 
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (user_id, today_start))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

# Singleton instance
logger = InteractionLogger()
