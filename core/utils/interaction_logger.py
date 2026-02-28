import os
from datetime import datetime
import json
from core.utils.db_utils import AsyncSQLite

class InteractionLogger:
    def __init__(self, db_path=None):
        if db_path is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            db_dir = os.path.join(root_dir, "data")
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
            db_path = os.path.join(db_dir, "mimi_interactions.db")
        
        self.db_path = db_path
        self.db = AsyncSQLite(db_path)
        self._init_db()

    def _init_db(self):
        import sqlite3
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

    async def log_interaction(self, user_id, user_input, intent, agent_thought, agent_output, tags=None, metadata=None):
        query = '''
            INSERT INTO interactions (timestamp, user_id, user_input, intent, agent_thought, agent_output, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            datetime.now().isoformat(),
            user_id,
            user_input,
            intent,
            agent_thought,
            agent_output,
            json.dumps(tags) if tags else None,
            json.dumps(metadata) if metadata else None
        )
        await self.db.execute(query, params)

    async def get_daily_interactions(self, user_id="default_user"):
        """Retrieves all interactions for the current day."""
        today_start = datetime.now().strftime("%Y-%m-%d") + "T00:00:00"
        query = '''
            SELECT user_input, intent, agent_output, timestamp 
            FROM interactions 
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        '''
        params = (user_id, today_start)
        return await self.db.fetch_all(query, params)

# Singleton instance
logger = InteractionLogger()
