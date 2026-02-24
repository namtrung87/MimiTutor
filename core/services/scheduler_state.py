import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

SCHEDULE_FILE = "daily_schedule.json"

class SchedulerState:
    def __init__(self):
        self.schedule_path = SCHEDULE_FILE

    def load_schedule(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.schedule_path):
            return []
        try:
            with open(self.schedule_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading schedule: {e}")
            return []

    def save_schedule(self, schedule: List[Dict[str, Any]]):
        try:
            with open(self.schedule_path, "w", encoding="utf-8") as f:
                json.dump(schedule, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving schedule: {e}")

    def update_task(self, task_id: str, updates: Dict[str, Any]):
        schedule = self.load_schedule()
        for task in schedule:
            if task.get("id") == task_id:
                task.update(updates)
                break
        self.save_schedule(schedule)

    def confirm_all(self):
        schedule = self.load_schedule()
        for task in schedule:
            task["is_confirmed"] = True
        self.save_schedule(schedule)

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        schedule = self.load_schedule()
        now = datetime.now()
        pending = []
        
        for task in schedule:
            if not task.get("is_confirmed") or task.get("reminded"):
                continue
            
            start_time_str = task.get("start_time")
            if not start_time_str:
                continue
                
            try:
                # Assuming start_time is in ISO format or similar
                start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                # Convert to local if needed, but let's assume naive/local for now as per user context
                if start_time.tzinfo:
                    start_time = start_time.replace(tzinfo=None) # Simple local comparison
                
                buffer_minutes = 10 # Default
                summary = task.get("summary", "").lower()
                
                if "giảng dạy" in summary or "teaching" in summary:
                    buffer_minutes = 120
                elif any(word in summary for word in ["mma", "boxing", "gym", "tập"]):
                    buffer_minutes = 15
                elif any(word in summary for word in ["code", "luận án", "deep work", "làm việc", "nghiên cứu"]):
                    buffer_minutes = 5
                
                reminder_threshold = start_time - timedelta(minutes=buffer_minutes)
                
                if now >= reminder_threshold:
                    pending.append(task)
            except Exception as e:
                print(f"Error parsing time for task {task.get('id')}: {e}")
                
        return pending

scheduler_state = SchedulerState()
