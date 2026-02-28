"""
Scheduler State — SQLite-backed storage for daily schedule and reminders.

Replaces the old JSON-based `daily_schedule.json` with atomic SQLite operations.
Backward-compatible API: load_schedule, save_schedule, get_pending_reminders, etc.
Auto-migrates existing JSON data on first run.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo
from core.utils.db_utils import AsyncSQLite

logger = logging.getLogger("scheduler_state")
LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scheduler.db")
LEGACY_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "daily_schedule.json")


class SchedulerState:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.db = AsyncSQLite(self.db_path)
        self._init_db()
        self._migrate_from_json()

    def _init_db(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schedule (
                    id TEXT PRIMARY KEY,
                    schedule_date TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    is_confirmed INTEGER DEFAULT 0,
                    reminded INTEGER DEFAULT 0,
                    reminded_at TEXT,
                    last_micro_reminded_at TEXT,
                    micro_reminders_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS nutrition_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_date TEXT DEFAULT (date('now', 'localtime')),
                    log_time TEXT DEFAULT (time('now', 'localtime')),
                    meal_desc TEXT,
                    estimated_calories INTEGER,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            ''')
            # Migration: add columns if they don't exist
            try:
                conn.execute("ALTER TABLE schedule ADD COLUMN last_micro_reminded_at TEXT")
                conn.execute("ALTER TABLE schedule ADD COLUMN micro_reminders_count INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Columns already exist
            conn.commit()

    def _migrate_from_json(self):
        """One-time migration from daily_schedule.json to SQLite."""
        if not os.path.exists(LEGACY_JSON):
            return

        try:
            with open(LEGACY_JSON, "r", encoding="utf-8") as f:
                old_data = json.load(f)

            if not old_data:
                return

            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                # Check if we already have data (avoid re-migration)
                count = conn.execute("SELECT COUNT(*) FROM schedule").fetchone()[0]
                if count > 0:
                    return

                for task in old_data:
                    task_date = task.get("date", "")
                    if not task_date and task.get("start_time"):
                        task_date = task["start_time"][:10]

                    conn.execute('''
                        INSERT OR IGNORE INTO schedule 
                        (id, schedule_date, summary, start_time, is_confirmed, reminded)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        task.get("id", ""),
                        task_date,
                        task.get("summary", ""),
                        task.get("start_time", ""),
                        1 if task.get("is_confirmed") else 0,
                        1 if task.get("reminded") else 0,
                    ))
                conn.commit()
                logger.info(f"Migrated {len(old_data)} tasks from daily_schedule.json to SQLite.")

            # Rename the old file so we don't migrate again
            os.rename(LEGACY_JSON, LEGACY_JSON + ".bak")
            logger.info("Renamed daily_schedule.json → daily_schedule.json.bak")
        except Exception as e:
            logger.error(f"JSON migration error: {e}")

    # ─────────────────────────────────────
    # Core API (backward-compatible)
    # ─────────────────────────────────────
    async def load_schedule(self, date: str = None) -> List[Dict[str, Any]]:
        """Load schedule for a given date (default: today)."""
        if date is None:
            date = datetime.now(LOCAL_TZ).date().isoformat()
        try:
            query = "SELECT * FROM schedule WHERE schedule_date = ? ORDER BY start_time"
            return await self.db.fetch_all(query, (date,))
        except Exception as e:
            logger.error(f"Error loading schedule: {e}")
            return []

    async def save_schedule(self, schedule: List[Dict[str, Any]]):
        """Save a list of tasks (merges with existing tasks for the same date)."""
        if not schedule:
            return
        try:
            # Determine the date from the first task
            first_date = schedule[0].get("date", "")
            if not first_date and schedule[0].get("start_time"):
                first_date = schedule[0]["start_time"][:10]

            async def _save(conn):
                for task in schedule:
                    task_id = task.get("id", "")
                    task_date = task.get("date", first_date)
                    if not task_date and task.get("start_time"):
                        task_date = task["start_time"][:10]
                    
                    summary = task.get("summary", "")
                    start_time = task.get("start_time", "")
                    is_confirmed = 1 if task.get("is_confirmed") else 0
                    reminded = 1 if task.get("reminded") else 0

                    # Check if exists to preserve status
                    cursor = conn.execute("SELECT is_confirmed, reminded FROM schedule WHERE id = ?", (task_id,))
                    existing = cursor.fetchone() if task_id else None

                    if existing:
                        # Preserve confirmed OR reminded status if incoming data is False
                        if not is_confirmed and existing[0]: is_confirmed = 1
                        if not reminded and existing[1]: reminded = 1
                        
                        conn.execute('''
                            UPDATE schedule 
                            SET schedule_date = ?, summary = ?, start_time = ?, is_confirmed = ?, reminded = ?
                            WHERE id = ?
                        ''', (task_date, summary, start_time, is_confirmed, reminded, task_id))
                    else:
                        conn.execute('''
                            INSERT INTO schedule
                            (id, schedule_date, summary, start_time, is_confirmed, reminded)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (task_id, task_date, summary, start_time, is_confirmed, reminded))

            await self.db.run_in_transaction(_save)
            logger.info(f"Saved/Updated {len(schedule)} schedule items for {first_date}")
        except Exception as e:
            logger.error(f"Error saving schedule: {e}")

    async def add_task(self, task: Dict[str, Any]):
        """Add a single task atomically."""
        try:
            task_date = task.get("schedule_date", "")
            if not task_date and task.get("start_time"):
                task_date = task["start_time"][:10]

            query = '''
                INSERT INTO schedule
                (id, schedule_date, summary, start_time, is_confirmed, reminded)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            params = (
                task.get("id", ""),
                task_date,
                task.get("summary", ""),
                task.get("start_time", ""),
                1 if task.get("is_confirmed") else 0,
                1 if task.get("reminded") else 0,
            )
            await self.db.execute(query, params)
        except Exception as e:
            logger.error(f"Error adding task: {e}")

    async def schedule_event(self, summary: str, time_str: str, date_str: str = None):
        """Schedules a generic event/reminder."""
        import uuid
        if not date_str:
            date_str = datetime.now(LOCAL_TZ).date().isoformat()
        
        # Ensure time_str is full ISO-like start_time: YYYY-MM-DDTHH:MM:SS
        if "T" not in time_str:
            full_start_time = f"{date_str}T{time_str}"
        else:
            full_start_time = time_str

        task = {
            "id": f"hw_{uuid.uuid4().hex[:8]}",
            "schedule_date": date_str,
            "summary": summary,
            "start_time": full_start_time,
            "is_confirmed": 1,
            "reminded": 0
        }
        await self.add_task(task)
        logger.info(f"Scheduled event: {summary} at {full_start_time}")

    async def get_ongoing_deep_work_events(self) -> List[Dict[str, Any]]:
        """Find events whose summary matches Deep Work triggers and are currently active."""
        now = datetime.now(LOCAL_TZ)
        today = now.date().isoformat()
        ongoing = []

        try:
            query = "SELECT * FROM schedule WHERE schedule_date = ? AND is_confirmed = 1"
            rows = await self.db.fetch_all(query, (today,))

            for task in rows:
                summary = task.get("summary", "").lower()
                if not any(word in summary for word in ["code", "luận án", "deep work", "nghiên cứu"]):
                    continue

                start_time_str = task.get("start_time", "")
                if not start_time_str:
                    continue

                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=LOCAL_TZ)
                    else:
                        start_time = start_time.astimezone(LOCAL_TZ)

                    # Assume Deep Work lasts 3 hours if not specified
                    end_time = start_time + timedelta(hours=3)

                    if start_time <= now <= end_time:
                        ongoing.append(task)

                except Exception as e:
                    logger.error(f"Error parsing time for active check {task.get('id')}: {e}")

        except Exception as e:
            logger.error(f"Error getting ongoing deep work events: {e}")

        return ongoing

    async def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Atomically update a task by ID."""
        try:
            set_parts = []
            values = []
            for key, val in updates.items():
                if key == "reminded" and val:
                    set_parts.append("reminded = 1")
                    set_parts.append("reminded_at = ?")
                    values.append(datetime.now(LOCAL_TZ).isoformat())
                elif key == "is_confirmed":
                    set_parts.append("is_confirmed = ?")
                    values.append(1 if val else 0)
                else:
                    set_parts.append(f"{key} = ?")
                    values.append(val)

            if not set_parts:
                return

            values.append(task_id)
            sql = f"UPDATE schedule SET {', '.join(set_parts)} WHERE id = ?"
            await self.db.execute(sql, tuple(values))
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")

    async def log_meal_exact(self, meal_desc: str, estimated_calories: int):
        """
        Ghi nhận bữa ăn bằng text tự nhiên và lượng calo do LLM đoán.
        """
        await self.db.execute(
            "INSERT INTO nutrition_log (meal_desc, estimated_calories) VALUES (?, ?)",
            (meal_desc, estimated_calories)
        )
        """
        Get tasks that should be reminded NOW based on buffer_minutes.
        Uses proper timezone-aware comparison with Asia/Ho_Chi_Minh.
        """
        now = datetime.now(LOCAL_TZ)
        today = now.date().isoformat()
        pending = []

        try:
            query = "SELECT * FROM schedule WHERE schedule_date = ? AND is_confirmed = 1 AND reminded = 0"
            rows = await self.db.fetch_all(query, (today,))

            for task in rows:
                start_time_str = task.get("start_time", "")
                if not start_time_str:
                    continue

                try:
                    # Parse start_time: could be ISO with or without timezone
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))

                    # Ensure timezone-aware (assume local if naive)
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=LOCAL_TZ)
                    else:
                        start_time = start_time.astimezone(LOCAL_TZ)

                    # Determine buffer based on task type
                    summary = task.get("summary", "").lower()
                    buffer_minutes = 10  # default

                    if "giảng dạy" in summary or "teaching" in summary:
                        buffer_minutes = 120
                    elif any(word in summary for word in ["mma", "boxing", "gym", "tập"]):
                        buffer_minutes = 15
                    elif any(word in summary for word in ["họp", "meeting", "đối tác", "call"]):
                        buffer_minutes = 10
                    elif any(word in summary for word in ["code", "luận án", "deep work", "làm việc", "nghiên cứu", "ngủ", "sleep", "đi ngủ", "wind-down"]):
                        buffer_minutes = 5

                    reminder_threshold = start_time - timedelta(minutes=buffer_minutes)

                    if now >= reminder_threshold:
                        pending.append(task)

                except Exception as e:
                    logger.error(f"Error parsing time for task {task.get('id')}: {e}")

        except Exception as e:
            logger.error(f"Error getting pending reminders: {e}")

        return pending

    async def get_todays_calories(self) -> dict:
        """
        Lấy tổng calo trong ngày hôm nay và danh sách các bữa đã ăn.
        """
        meals = await self.db.fetch_all(
            "SELECT estimated_calories, meal_desc, log_time FROM nutrition_log WHERE log_date = date('now', 'localtime') ORDER BY id ASC"
        )
        
        total = sum(m["estimated_calories"] for m in meals if m["estimated_calories"] is not None)
        meals_list = [{"calories": m["estimated_calories"], "desc": m["meal_desc"], "time": m["log_time"]} for m in meals]
        
        goal = int(os.getenv("DAILY_CALORIE_GOAL", "2100"))
        return {
            "total_calories": total,
            "goal": goal,
            "remaining": goal - total,
            "meals": meals_list
        }

    async def get_calorie_balance(self, date_str: str = None) -> int:
        """Returns (total_calories - goal) for a given date (default: yesterday)."""
        if date_str is None:
            # Use yesterday's date
            date_str = (datetime.now(LOCAL_TZ) - timedelta(days=1)).date().isoformat()
        
        query = "SELECT SUM(estimated_calories) FROM nutrition_log WHERE log_date = ?"
        row = await self.db.fetch_one(query, (date_str,))
        total = row[0] if row and row[0] is not None else 0
        
        goal = int(os.getenv("DAILY_CALORIE_GOAL", "2100"))
        return total - goal

    async def confirm_all(self, date_str: str = None):
        """Mark all scheduled items for a given date as confirmed (is_confirmed=1)."""
        if date_str is None:
            date_str = datetime.now(LOCAL_TZ).date().isoformat()
        await self.db.execute(
            "UPDATE schedule SET is_confirmed = 1 WHERE schedule_date = ?",
            (date_str,)
        )
        logger.info(f"Confirmed all schedule items for {date_str}")

# Global instance
scheduler_state = SchedulerState()
