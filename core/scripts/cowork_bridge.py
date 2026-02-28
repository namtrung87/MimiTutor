import os
import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path

# Paths
DB_PATH = r"E:\Drive\Antigravitiy\Orchesta assistant\data\conversations.db"
COWORK_DATA_PATH = r"E:\Drive\Antigravitiy\Orchesta assistant\data\cowork_sync.json"

def sync_memory(limit=20):
    """Pulls recent Telegram history and exports it for the assistant context."""
    if not os.path.exists(DB_PATH):
        print(f"[ERR] DB not found at {DB_PATH}")
        return

    print(f"Syncing last {limit} messages from Telegram...")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT role, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT ?", 
            (limit,)
        )
        messages = [dict(r) for r in cursor.fetchall()]
        messages.reverse()
        
        # Save to a format the assistant can easily read next time
        sync_data = {
            "last_sync": datetime.now().isoformat(),
            "telegram_history": messages
        }
        
        with open(COWORK_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(sync_data, f, indent=2, ensure_ascii=False)
            
        print(f"[OK] Memory synced to {COWORK_DATA_PATH}")
    except Exception as e:
        print(f"[ERR] Sync failed: {e}")

def push_notification(message):
    """Allows the assistant to 'push' a status update to the local system/log."""
    log_path = r"E:\Drive\Antigravitiy\Orchesta assistant\orchesta_bot.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} [COWORK_AGENT] {message}\n")
    print(f"[OK] Notification pushed to logs.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity-Cowork Bridge")
    parser.add_argument("--sync", action="store_true", help="Sync memory from DB")
    parser.add_argument("--notify", type=str, help="Push a notification message")
    
    args = parser.parse_args()
    
    if args.sync:
        sync_memory()
    if args.notify:
        push_notification(args.notify)
