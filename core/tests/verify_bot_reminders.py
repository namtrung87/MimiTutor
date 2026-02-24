import asyncio
import datetime
from core.heartbeat_manager import HeartbeatManager
from core.services.scheduler_state import scheduler_state

async def verify_logic():
    hb = HeartbeatManager(interval_minutes=1)
    
    # 1. Test Daily Briefing (Simulate morning)
    print("\n--- Testing Daily Briefing ---")
    # We'll manually trigger it once
    # Since we can't easily mock datetime.now() globally without extra libs, 
    # let's just check if it fails or runs quietly given current time.
    hb.daily_briefing_probe()
    
    # 2. Test Reminders (Manually inject tasks)
    print("\n--- Testing Reminders ---")
    now = datetime.datetime.now()
    test_tasks = [
        {
            "id": "test_gym",
            "summary": "Tập gym MMA",
            "start_time": (now + datetime.timedelta(minutes=14)).isoformat(), # Should trigger (15m buffer)
            "is_confirmed": True,
            "reminded": False
        },
        {
            "id": "test_teaching",
            "summary": "Giảng dạy ACCA",
            "start_time": (now + datetime.timedelta(hours=1, minutes=55)).isoformat(), # Should trigger (120m buffer)
            "is_confirmed": True,
            "reminded": False
        }
    ]
    scheduler_state.save_schedule(test_tasks)
    
    print("Checking reminders for tasks starting soon...")
    hb.reminder_probe()
    
    # Check if they were marked as reminded
    updated_schedule = scheduler_state.load_schedule()
    for task in updated_schedule:
        print(f"Task '{task['summary']}' - Reminded: {task['reminded']}")

if __name__ == "__main__":
    asyncio.run(verify_logic())
