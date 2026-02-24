import os
import time
import datetime
import asyncio
from typing import List, Callable
from core.utils.memory_manager import memory_manager
from core.utils.interaction_logger import logger as interaction_logger
from skills.google_calendar.calendar_client import CalendarClient
from core.services.telegram_service import telegram_service
from core.services.scheduler_state import scheduler_state
from core.utils.z_research import ZResearch

class HeartbeatManager:
    """
    Heartbeat Engine inspired by OpenClaw.
    Periodically runs 'probes' to detect state changes and notify the user/agent system.
    """
    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes * 60
        self.probes: List[Callable] = []
        self.is_running = False
        self.researcher = ZResearch()
        
        # Initialize probes
        self._setup_probes()

    def _setup_probes(self):
        self.probes.append(self.calendar_probe)
        self.probes.append(self.memory_summary_probe)
        self.probes.append(self.checklist_probe)
        self.probes.append(self.evolution_probe)
        self.probes.append(self.mimi_audit_probe)
        self.probes.append(self.daily_briefing_probe)
        self.probes.append(self.reminder_probe)

    def notify(self, message: str):
        """Sends a proactive notification to the user."""
        print(f"  [Heartbeat] Notification: {message}")
        if telegram_service.token:
            try:
                # Run the async notification correctly
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        loop.create_task(telegram_service.send_message(message))
                    else:
                        asyncio.run(telegram_service.send_message(message))
                except RuntimeError:
                    # No running loop
                    asyncio.run(telegram_service.send_message(message))
            except Exception as e:
                print(f"  [Heartbeat] Failed to send Telegram: {e}")

    def calendar_probe(self):
        """Checks for upcoming events in the next 24 hours."""
        print("  [Heartbeat] Running Calendar Probe...")
        try:
            client = CalendarClient()
            now = datetime.datetime.now(datetime.timezone.utc)
            tomorrow = now + datetime.timedelta(days=1)
            events = client.list_events(max_results=10, time_min=now.isoformat())
            
            upcoming = []
            for event in events:
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                # Simple string check for 'tomorrow' or 'today' logic
                # For now, just list them
                upcoming.append(f"- {start_str}: {event['summary']}")
            
            if upcoming:
                print(f"  [Heartbeat] Found {len(upcoming)} upcoming events.")
                self.notify(f"You have {len(upcoming)} upcoming events in the next 24h:\n" + "\n".join(upcoming[:3]))
        except Exception as e:
            print(f"  [Heartbeat] Calendar Probe Error: {e}")

    def memory_summary_probe(self):
        """Ensures BRAIN.md is up to date with long-term memory."""
        print("  [Heartbeat] Running Memory Summary Probe...")
        try:
            user_id = "default_user" # Should be dynamic
            memories = memory_manager.get_all_memories(user_id)
            
            brain_path = "BRAIN.md"
            with open(brain_path, "w", encoding="utf-8") as f:
                f.write("# Orchesta Assistant: Transparent Memory (BRAIN.md)\n\n")
                f.write("> This file is automatically updated by the Heartbeat Engine.\n\n")
                f.write("## Long-Term Memories\n")
                if not memories:
                    f.write("No memories found.\n")
                for m in memories:
                    text = m.get('memory') or m.get('text')
                    f.write(f"- {text}\n")
            print(f"  [Heartbeat] Synchronized {len(memories)} memories to BRAIN.md")
        except Exception as e:
            print(f"  [Heartbeat] Memory Probe Error: {e}")

    def checklist_probe(self):
        """Checks for a HEARTBEAT.md file for pending manual tasks."""
        print("  [Heartbeat] Running Checklist Probe...")
        checklist_path = "HEARTBEAT.md"
        if os.path.exists(checklist_path):
            with open(checklist_path, "r", encoding="utf-8") as f:
                tasks = f.read()
                # If there are unchecked boxes, consider it "active"
                if "[ ]" in tasks:
                    print("  [Heartbeat] Pending tasks detected in HEARTBEAT.md")
                    self.notify("You have pending tasks in HEARTBEAT.md that need attention.")
        else:
            # Create a template if it doesn't exist
            with open(checklist_path, "w", encoding="utf-8") as f:
                f.write("# Pending Tasks (HEARTBEAT.md)\n\n")
                f.write("- [ ] Review today's schedule\n")
                f.write("- [ ] Check research results\n")

    def evolution_probe(self):
        """Analyzes BRAIN.md for potential new skills to extract."""
        print("  [Heartbeat] Running Evolution Probe...")
        brain_path = "BRAIN.md"
        checklist_path = "HEARTBEAT.md"
        
        if not os.path.exists(brain_path): return

        try:
            with open(brain_path, "r", encoding="utf-8") as f:
                content = f.read()

            prompt = f"""
            Analyze the following distilled long-term memories and identify recurring patterns, 
            complex workflows, or technical procedures that SHOULD be codified as a specialized "Skill Card".
            
            Memories:
            {content}
            
            Return a short list of potential skills (titles only) that aren't already represented as clear procedures.
            Format your response as a simple bulleted list. If nothing new is found, return "No new skills suggested."
            """
            
            suggestions = self.researcher.query(prompt)
            if "No new skills suggested" not in suggestions:
                print(f"  [Heartbeat] Evolution suggestions found.")
                with open(checklist_path, "a", encoding="utf-8") as f:
                    f.write(f"\n## Skill Evolution Suggestions ({datetime.date.today()})\n")
                    for line in suggestions.split("\n"):
                        if line.strip().startswith("-") or line.strip().startswith("*"):
                            f.write(f"- [ ] Extract skill: {line.strip()[1:].strip()}\n")
                
                self.notify("The Evolution Probe has suggested new skill extractions. Check HEARTBEAT.md.")

        except Exception as e:
            print(f"  [Heartbeat] Evolution Probe Error: {e}")

    def mimi_audit_probe(self):
        """Analyzes Mimi's daily interactions and reports to the user."""
        print("  [Heartbeat] Running Mimi Audit Probe...")
        try:
            interactions = interaction_logger.get_daily_interactions()
            if not interactions:
                print("  [Heartbeat] No Mimi interactions found for today.")
                return

            # Format interactions for LLM
            history_text = ""
            for i in interactions:
                history_text += f"Time: {i['timestamp']}\nUser: {i['user_input']}\nAgent: {i['agent_output']}\n---\n"

            prompt = f"""
            Analyze the following chatbot interactions between "Mimi" (a Grade 7 student) and her AI tutor.
            
            Interactions:
            {history_text}
            
            Please provide a concise report for the parents covering:
            1. **Topics & Questions**: What did Mimi learn or ask about today?
            2. **Attitude & Engagement**: What was Mimi's attitude (e.g., curious, frustrated, bored)? 
            3. **Struggles**: Which topics or concepts did she seem to have difficulty with?
            4. **Recommendations**: A brief suggestion for the parent on how to support her further.

            Response should be in VIETNAMESE, engaging, and professional.
            """
            
            summary = self.researcher.query(prompt)
            if summary:
                self.notify(f"📊 **Mimi Learning Report ({datetime.date.today()}):**\n\n{summary}")
        except Exception as e:
            print(f"  [Heartbeat] Mimi Audit Probe Error: {e}")

    def daily_briefing_probe(self):
        """Sends a morning briefing with today's schedule."""
        now = datetime.datetime.now()
        # Only run between 7 AM and 9 AM if not already briefed today
        if not (7 <= now.hour <= 9):
            return
            
        schedule = scheduler_state.load_schedule()
        today_date = now.date().isoformat()
        
        # Check if we already have today's schedule briefed/saved
        if schedule and any(task.get("date") == today_date for task in schedule):
            return

        print("  [Heartbeat] Generating Daily Briefing...")
        try:
            client = CalendarClient()
            events = client.list_events(max_results=20, time_min=datetime.datetime.combine(now.date(), datetime.time.min).isoformat() + "Z")
            
            new_schedule = []
            briefing_msg = "☀️ **Chào buổi sáng, Trung Nguyen!**\n\nĐây là lịch trình hôm nay của bạn:\n"
            
            for event in events:
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'No Title')
                task_id = event.get('id', start_str + summary)
                
                new_schedule.append({
                    "id": task_id,
                    "date": today_date,
                    "summary": summary,
                    "start_time": start_str,
                    "is_confirmed": False,
                    "reminded": False
                })
                briefing_msg += f"- {start_str[11:16] if 'T' in start_str else 'All Day'}: {summary}\n"
            
            if not new_schedule:
                briefing_msg += "Hôm nay bạn không có lịch trình nào đặc biệt trên Calendar."
            
            briefing_msg += "\n\n**Bạn chốt lịch này chứ?** (Trả lời 'OK' hoặc 'Chốt' để tôi bắt đầu nhắc nhở di chuyển)."
            
            scheduler_state.save_schedule(new_schedule)
            self.notify(briefing_msg)
        except Exception as e:
            print(f"  [Heartbeat] Briefing Probe Error: {e}")

    def reminder_probe(self):
        """Checks for upcoming tasks and sends timely reminders."""
        print("  [Heartbeat] Running Reminder Probe...")
        pending = scheduler_state.get_pending_reminders()
        
        for task in pending:
            summary = task.get("summary", "")
            start_time_str = task.get("start_time", "")
            time_part = start_time_str[11:16] if "T" in start_time_str else "đúng giờ"
            
            msg = f"🔔 **Nhắc nhở:** Sắp đến giờ thực hiện: *{summary}* lúc {time_part}.\n"
            
            if "giảng dạy" in summary.lower() or "teaching" in summary.lower():
                msg += "🚀 Đây là giờ đi dạy, bạn cần di chuyển ngay bây giờ (mất 2 tiếng) để kịp giờ."
            elif any(word in summary.lower() for word in ["mma", "boxing", "gym", "tập"]):
                msg += "👟 Đã đến lúc chuẩn bị đồ đạc và di chuyển đi tập (15 phút nữa bắt đầu)."
            elif any(word in summary.lower() for word in ["họp", "meeting", "đối tác", "call"]):
                msg += "💼 Sắp đến giờ họp/gặp gỡ. Vui lòng chuẩn bị tài liệu và tác phong nhé."
            elif any(word in summary.lower() for word in ["code", "luận án", "deep work", "làm", "nghiên cứu"]):
                msg += "🧠 Chuẩn bị vào block làm việc tập trung. Hãy lấy thêm nước và bật chế độ không làm phiền (DND) nhé!"
            else:
                msg += "Vui lòng chuẩn bị sẵn sàng."
                
            self.notify(msg)
            scheduler_state.update_task(task["id"], {"reminded": True})

    def run_once(self):
        """Runs all probes once."""
        print(f"\n--- Heartbeat Tick: {datetime.datetime.now()} ---")
        for probe in self.probes:
            probe()

    def start(self):
        """Starts the periodic heartbeat loop."""
        self.is_running = True
        print(f"Starting Heartbeat Engine (every {self.interval/60} mins)...")
        while self.is_running:
            self.run_once()
            time.sleep(self.interval)

if __name__ == "__main__":
    # Test run
    hb = HeartbeatManager(interval_minutes=1) # Fast interval for testing
    hb.run_once()
