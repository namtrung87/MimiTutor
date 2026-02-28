"""
Unified Heartbeat Service for Orchesta Assistant.
Replaces the scattered heartbeat/scheduler layers with a single async engine.

Jobs:
  - morning_sync        : 7:00 AM — Daily briefing + schedule
  - trendscout_briefing : 7:15 AM — TrendScout intelligence
  - evening_wrapup      : 21:00   — End-of-day summary
  - mimi_daily_report   : 21:30   — Mimi learning report
  - check_reminders     : every 5 min — Task/event reminders
  - memory_sync         : 3:00 AM — Sync BRAIN.md
  - evolution_check     : Sunday 10:00 AM — Skill evolution
"""

import os
import logging
import datetime
from zoneinfo import ZoneInfo
from telegram import Bot
from telegram.constants import ParseMode
import json
import asyncio

from core.services.scheduler_state import scheduler_state
from core.services.night_shift import night_shift
from core.utils.llm_manager import LLMManager
from core.agents.gmail_executive_agent import GmailExecutiveAgent
from skills.commute_planner.commute_calculator import CommutePlanner

logger = logging.getLogger("heartbeat")
LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class HeartbeatService:
    """Unified async heartbeat engine for Telegram bot."""

    def __init__(self, bot: Bot, user_id: str):
        self.bot = bot
        self.user_id = user_id

    # ─────────────────────────────────────
    # Public API
    # ─────────────────────────────────────
    def register_jobs(self, scheduler):
        """Register all heartbeat jobs onto the given AsyncIOScheduler."""
        # Morning block - Consolidated at 7:00 AM
        scheduler.add_job(self.morning_sync, 'cron', hour=7, minute=0, id='hb_morning')

        # Evening block
        scheduler.add_job(self.evening_wrapup, 'cron', hour=21, minute=0, id='hb_evening')
        scheduler.add_job(self.mimi_daily_report, 'cron', hour=21, minute=30, id='hb_mimi')

        # Recurring (5 min instead of 1 min — saves 80% I/O)
        scheduler.add_job(self.check_reminders, 'interval', minutes=5, id='hb_reminders')

        # Off-peak maintenance (DISABLED by user request)
        # scheduler.add_job(self.memory_sync, 'cron', hour=3, minute=0, id='hb_memory')
        # scheduler.add_job(self.evolution_check, 'cron', day_of_week='sun', hour=10, id='hb_evolution')

        logger.info("HeartbeatService: 7 jobs registered.")

    # ─────────────────────────────────────
    # Helper: safe Telegram send
    # ─────────────────────────────────────
    async def _send(self, text: str):
        """Send a message to the user, with Markdown fallback."""
        if not self.bot or not self.user_id:
            logger.warning(f"Telegram not configured. Msg: {text[:100]}")
            return
        try:
            await self.bot.send_message(
                chat_id=self.user_id, text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            try:
                await self.bot.send_message(
                    chat_id=self.user_id, text=text,
                    parse_mode=None
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")

    # ─────────────────────────────────────
    # Job 1: Morning Sync (7:00 AM)
    # ─────────────────────────────────────
    async def morning_sync(self):
        """Unified morning briefing: Readiness + Sleep + NightShift + Tasks + Calendar + Gmail + Trends."""
        logger.info("Running unified morning_sync...")
        
        data = {}
        
        # 1. Gather Health Data
        try:
            from skills.wellness.oura_client import OuraClient
            oura = OuraClient()
            data['readiness'] = oura.get_readiness_score().get("score", "N/A")
        except: data['readiness'] = "N/A"

        try:
            health_path = "data/apple_health.json"
            if os.path.exists(health_path):
                with open(health_path, "r", encoding="utf-8") as f:
                    health_list = json.load(f)
                    if health_list:
                        latest = sorted(health_list, key=lambda x: x.get("date", ""), reverse=True)[0]
                        data['sleep'] = f"{latest.get('time_asleep_hours')}h (In bed: {latest.get('time_in_bed_hours')}h)"
        except: data['sleep'] = "N/A"

        # 2. Night Shift
        try:
            jobs = await night_shift.get_completed_jobs_since(12)
            data['night_shift'] = [j['name'] for j in jobs]
        except: data['night_shift'] = []

        # 3. Tasks & Calendar
        try:
            from core.utils.task_manager import task_manager
            tasks = await task_manager.get_pending_tasks(str(self.user_id))
            data['tasks'] = [t['desc'] for t in tasks]
            
            from skills.google_calendar.calendar_client import CalendarClient
            now = datetime.datetime.now(LOCAL_TZ)
            cal = CalendarClient()
            events = cal.list_events(max_results=10, time_min=datetime.datetime.combine(now.date(), datetime.time.min, tzinfo=LOCAL_TZ).isoformat())
            data['calendar'] = [f"{e['start'].get('dateTime', 'All Day')[11:16]}: {e.get('summary')}" for e in events]
        except: 
            data['tasks'] = []
            data['calendar'] = []

        # 4. Trends (TrendScout)
        try:
            from core.agents.trendscout_agent import TrendScoutAgent
            ts = TrendScoutAgent()
            data['trends'] = ts.generate_daily_briefing()
        except: data['trends'] = "No trend data available."

        # 5. Unified Synthesis
        llm = LLMManager()
        prompt = f"""
        Bạn là Personal Strategic Advisor. Hãy tổng hợp báo cáo sáng sớm cho chủ nhân.
        
        DỮ LIỆU GỐC:
        - Readiness: {data.get('readiness')}
        - Sleep: {data.get('sleep')}
        - Night Shift: {data.get('night_shift')}
        - Tasks: {data.get('tasks')}
        - Calendar: {data.get('calendar')}
        - Market/Tech Trends: {data.get('trends')}
        
        YÊU CẦU:
        1. Viết tin nhắn Telegram (Markdown) cực kỳ chuyên nghiệp, sắc bén và truyền cảm hứng.
        2. Chia làm các phần: Sức khỏe, Công việc (Lịch & Task), và Radar (Trend).
        3. Cuối cùng, đưa ra 1 "Strategy of the Day".
        4. Dùng tiếng Việt.
        """
        try:
            briefing = await asyncio.to_thread(llm.query, prompt, complexity="L2")
            await self._send(briefing)
        except Exception as e:
            logger.error(f"Unified briefing synthesis failed: {e}")
            await self._send("⚠️ Lỗi khi tổng hợp báo cáo sáng sớm. Vui lòng kiểm tra log.")

    # ─────────────────────────────────────
    # Job 3: Evening Wrap-up (21:00)
    # ─────────────────────────────────────
    async def evening_wrapup(self):
        """Send end-of-day summary and PROPOSE tomorrow's optimized schedule (9:00 PM)."""
        logger.info("Running expanded evening_wrapup + schedule proposal...")
        now = datetime.datetime.now(LOCAL_TZ)
        tomorrow = now + datetime.timedelta(days=1)
        tomorrow_date = tomorrow.date().isoformat()
        
        # 1. Today's Summary
        today_summary = ""
        try:
            from core.utils.task_manager import task_manager
            completed = await task_manager.get_completed_tasks_today(str(self.user_id))
            pending = await task_manager.get_pending_tasks(str(self.user_id))
            today_summary += f"✅ Hoàn thành: {len(completed)} | ⏳ Còn lại: {len(pending)}"
        except Exception: pass

        # 2. Fetch tomorrow's Google Calendar events
        calendar_events = []
        try:
            from skills.google_calendar.calendar_client import CalendarClient
            client = CalendarClient()
            events = client.list_events(
                max_results=15,
                time_min=datetime.datetime.combine(tomorrow.date(), datetime.time.min, tzinfo=LOCAL_TZ).isoformat(),
                time_max=datetime.datetime.combine(tomorrow.date(), datetime.time.max, tzinfo=LOCAL_TZ).isoformat()
            )
            for e in events:
                start = e['start'].get('dateTime', e['start'].get('date'))
                calendar_events.append({
                    "summary": e.get('summary', 'No Title'),
                    "start": start,
                    "id": e.get('id')
                })
        except Exception as e:
            logger.error(f"evening_wrapup: calendar error: {e}")

        # 3. Commute Planning for tomorrow
        commute_advice = ""
        try:
            planner = CommutePlanner()
            # Find the first event that might require travel
            travel_event = None
            for e in calendar_events:
                summary = e['summary'].lower()
                if any(word in summary for word in ["teaching", "giảng dạy", "họp", "đối tác", "gym", "mma"]):
                    travel_event = e
                    break
            
            if travel_event:
                dest = travel_event['summary']
                target_time = travel_event['start'][11:16] if 'T' in travel_event['start'] else "08:00"
                # Load locations from commute_state.json
                commute_state_path = os.path.join(os.path.dirname(__file__), "..", "..", "commute_state.json")
                origin = "Home"
                if os.path.exists(commute_state_path):
                    with open(commute_state_path, "r", encoding="utf-8") as f:
                        c_state = json.load(f)
                        origin = c_state.get("locations", {}).get("home", "Home")
                
                plan = await planner.get_travel_plan(origin, dest, target_time)
                if "options" in plan:
                    commute_advice = "\n🚢 *Phương án di chuyển DỰ THẢO (AI tra cứu):*\n"
                    for opt in plan["options"]:
                        rec = " (Khuyên dùng)" if opt.get("is_recommended") else ""
                        commute_advice += f"- {opt['mode']}: {opt['route_desc']} - {opt['estimated_cost_vnd']}đ - Xuất phát: {opt['departure_time']}{rec}\n"
                    commute_advice += f"\n💡 *Lưu ý:* Đây là phương án AI tìm kiếm, có thể chưa khớp 100% với lộ trình thực tế của anh.\n"
        except Exception as e:
            logger.error(f"evening_wrapup: commute planner error: {e}")

        # 4. AI Proposal Generation
        report_msg = "🌙 *End-of-Day Heartbeat & Tomorrow's Strategy*\n\n"
        try:
            llm = LLMManager()
            prompt = f"""
            Bạn là Personal Strategy Assistant. Hôm nay là {now.date()}. 
            DỮ LIỆU NGÀY MAI ({tomorrow_date}):
            Lịch Calendar: {json.dumps(calendar_events, ensure_ascii=False)}
            Gợi ý di chuyển: {commute_advice}

            NGUYÊN TẮC XẾP LỊCH:
            1. Ưu tiên Deep Work (90-120p) vào buổi sáng (8h-11h) hoặc khi không có lịch họp/dạy.
            2. Chèn 20p NSDR/Nghỉ ngơi vào lúc 2h chiều.
            3. Nếu có lịch MMA/Gym (thường buổi chiều tối), hãy nhắc nạp Pre-workout 30p trước đó.
            4. Tech Curfew từ 21:30.
            
            NHIỆM VỤ:
            Hãy tạo một lịch trình đề xuất tối ưu cho ngày mai. 
            Kết quả trả về gồm:
            1. Tóm tắt nhanh thành tích hôm nay: {today_summary}
            2. Bảng lịch trình đề xuất (giờ: nội dung).
            3. Một lời khuyên chiến thuật cho ngày mai.
            4. ĐẶC BIỆT: Nếu có phần di chuyển ({commute_advice}), hãy đưa ra câu hỏi xác nhận: 
               "Lộ trình phía trên chỉ là dự thảo. Anh có muốn chốt chính xác đi tuyến xe bus nào, số mấy hoặc đổi lộ trình như thế nào không để em lưu lại lời nhắc chính xác nhất cho sáng mai?"
            
            Dùng tiếng Việt, chuyên nghiệp.
            """
            ai_res = await asyncio.to_thread(llm.query, prompt, complexity="L2")
            
            # Extract JSON and Text
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', ai_res, re.DOTALL)
            proposal_text = re.sub(r'```json.*?```', '', ai_res, flags=re.DOTALL).strip()
            
            if json_match:
                try:
                    proposal_data = json.loads(json_match.group(1))
                    # Save to scheduler_state with is_confirmed=0
                    new_tasks = []
                    for item in proposal_data:
                        new_tasks.append({
                            "id": f"prop_{datetime.datetime.now().timestamp()}_{item.get('id')}",
                            "date": tomorrow_date,
                            "summary": item.get('summary'),
                            "start_time": item.get('start_time'),
                            "is_confirmed": False,
                            "reminded": False
                        })
                    if new_tasks:
                        await scheduler_state.save_schedule(new_tasks)
                        proposal_text += "\n\n👉 *Nhắn 'Chốt' để tôi kích hoạt lịch này và bắt đầu nhắc nhở vào ngày mai.*"
                except Exception as e:
                    logger.error(f"Proposal JSON parse error: {e}")

            report_msg += proposal_text
        except Exception as e:
            logger.error(f"evening_wrapup: AI synthesis error: {e}")
            report_msg += "Lỗi khi tạo chiến lược AI. Vui lòng kiểm tra log."

        await self._send(report_msg)

    # ─────────────────────────────────────
    # Job 4: Mimi Daily Report (21:30)
    # ─────────────────────────────────────
    async def mimi_daily_report(self):
        """Analyze Mimi's daily interactions and report to parents."""
        logger.info("Running mimi_daily_report...")
        try:
            from core.utils.interaction_logger import interaction_logger
            interactions = await interaction_logger.get_daily_interactions()
            if not interactions:
                logger.info("No Mimi interactions found for today.")
                return

            history_text = ""
            for i in interactions:
                history_text += f"Time: {i['timestamp']}\nUser: {i['user_input']}\nAgent: {i['agent_output']}\n---\n"

            from core.utils.z_research import ZResearch
            researcher = ZResearch()
            prompt = f"""
            Analyze the following chatbot interactions between "Mimi" (a Grade 7 student) and her AI tutor.
            
            Interactions:
            {history_text}
            
            Please provide a concise report for the parents covering:
            1. **Topics & Questions**: What did Mimi learn or ask about today?
            2. **Attitude & Engagement**: What was Mimi's attitude?
            3. **Struggles**: Which topics or concepts did she have difficulty with?
            4. **Recommendations**: Brief suggestion for the parent.

            Response should be in VIETNAMESE, engaging, and professional.
            """
            summary = researcher.query(prompt, complexity="L2")
            if summary:
                today = datetime.date.today().isoformat()
                await self._send(f"📊 *Mimi Learning Report ({today}):*\n\n{summary}")
        except Exception as e:
            logger.error(f"mimi_daily_report error: {e}")

    # ─────────────────────────────────────
    # Job 5: Check Reminders (every 5 min)
    # ─────────────────────────────────────
    async def check_reminders(self):
        """Check for upcoming tasks and send timely reminders. Per-task error isolation."""
        try:
            # 1. Manual tasks (tasks.db)
            from core.utils.task_manager import task_manager
            due_tasks = await task_manager.get_due_tasks(str(self.user_id))
            for t in due_tasks:
                try:
                    msg = f"⏰ *Nhắc việc đến giờ:*\n\n- `{t['desc']}`\n\nGõ `/done {t['id']}` sau khi hoàn thành."
                    await self._send(msg)
                except Exception as e:
                    logger.error(f"Reminder failed for manual task {t.get('id')}: {e}")
        except Exception as e:
            logger.error(f"check_reminders task_manager error: {e}")

        # 2. Planned daily schedule (SQLite)
        try:
            pending_reminders = await scheduler_state.get_pending_reminders()
            for r in pending_reminders:
                try:
                    await self._send_schedule_reminder(r)
                    await scheduler_state.update_task(r.get('id'), {"reminded": True})
                except Exception as e:
                    logger.error(f"Reminder failed for scheduled task {r.get('id')}: {e}")
        except Exception as e:
            logger.error(f"check_reminders scheduler_state error: {e}")

        # 3. Active Deep Work habits (NEW)
        try:
            active_events = await scheduler_state.get_ongoing_deep_work_events()
            for event in active_events:
                await self._check_deep_work_habits(event)
        except Exception as e:
            logger.error(f"check_reminders deep_work_habits error: {e}")

    async def _check_deep_work_habits(self, event: dict):
        """Send recurrent micro-habit reminders during an active focus block."""
        now = datetime.datetime.now(LOCAL_TZ)
        event_id = event.get('id')
        last_reminded_str = event.get('last_micro_reminded_at')
        count = event.get('micro_reminders_count', 0)

        # Parse start time to calculate duration
        try:
            start_time = datetime.datetime.fromisoformat(event['start_time'].replace("Z", "+00:00"))
            if start_time.tzinfo is None: start_time = start_time.replace(tzinfo=LOCAL_TZ)
            else: start_time = start_time.astimezone(LOCAL_TZ)
        except Exception:
            return

        minutes_since_start = (now - start_time).total_seconds() / 60
        
        last_reminded = None
        if last_reminded_str:
            try:
                last_reminded = datetime.datetime.fromisoformat(last_reminded_str)
            except Exception:
                pass
        
        minutes_since_last = 999
        if last_reminded:
            minutes_since_last = (now - last_reminded).total_seconds() / 60

        # Logic: 
        # 1. First micro-reminder at 30 mins
        # 2. Re-trigger every 30 mins (20-20-20 rule)
        # 3. Special reminder at 90 mins (Micro-break)
        
        msg = ""
        if minutes_since_start >= 30 and minutes_since_last >= 30:
            if 85 <= minutes_since_start <= 100: # Near 90 min mark
                msg = "🚶 *Micro-Break (90p Focus):* Đã đến lúc đứng dậy vươn vai 2 phút, đi lấy thêm trà/nước để làm mới não bộ nhé!"
            else:
                msg = "👁️ *Quy tắc 20-20-20 (30p Focus):* Hãy nhìn xa 6m trong 20s và uống 1 ngụm nước để bảo vệ mắt và não."
        
        if msg:
            await self._send(msg)
            await scheduler_state.update_task(event_id, {
                "last_micro_reminded_at": now.isoformat(),
                "micro_reminders_count": count + 1
            })

    async def _send_schedule_reminder(self, task: dict):
        """Format and send a context-aware reminder for a scheduled task."""
        summary = task.get('summary', 'Sự kiện')
        start = task.get('start_time', '')[11:16] if 'T' in task.get('start_time', '') else task.get('start_time', '')
        msg = f"🔔 *Sắp đến giờ:* `{summary}` lúc {start}\n\n"

        # Check for confirmed commute override
        commute_info = ""
        try:
            commute_state_path = os.path.join(os.path.dirname(__file__), "..", "..", "commute_state.json")
            if os.path.exists(commute_state_path):
                with open(commute_state_path, "r", encoding="utf-8") as f:
                    c_state = json.load(f)
                    confirmed = c_state.get("confirmed_commute")
                    if confirmed and confirmed.get("date") == datetime.datetime.now().strftime("%Y-%m-%d"):
                        commute_info = f"\n📍 **Lộ trình đã chốt:** {confirmed.get('route_desc')}"
                        if confirmed.get("departure_time"):
                            commute_info += f" (Xuất phát: {confirmed.get('departure_time')})"
        except Exception:
            pass

        s_lower = summary.lower()
        if "ngủ" in s_lower or "sleep" in s_lower or "wind-down" in s_lower:
            msg += "💤 Đã đến lúc gác lại công việc, chuẩn bị vệ sinh cá nhân và đi ngủ để hồi phục năng lượng nhé!"
        elif any(word in s_lower for word in ["giảng dạy", "teaching"]):
            msg += f"🚀 Đây là giờ đi dạy. {commute_info if commute_info else '*Hãy kiểm tra lộ trình xe bus hoặc đặt Grab/Be ngay để đảm bảo đến đúng giờ.*'} Đừng quên chuẩn bị tài liệu giảng dạy nhé!"
        elif any(word in s_lower for word in ["mma", "boxing", "gym", "tập"]):
            msg += f"👟 Đã đến lúc chuẩn bị đồ đạc và chuẩn bị đi tập rồi! {commute_info if commute_info else '*Đừng quên pha một bình nước điện giải để bù khoáng nhé.*'}"
        elif any(word in s_lower for word in ["họp", "meeting", "đối tác", "call"]):
            msg += f"💼 Sắp đến giờ họp/gặp gỡ. {commute_info if commute_info else '*Nếu cần di chuyển, hãy kiểm tra tình hình giao thông trên Google Maps trước khi đi.*'}"
        elif any(word in s_lower for word in ["code", "luận án", "deep work", "nghiên cứu"]):
            msg += "🧠 Chuẩn bị vào block làm việc tập trung. *Hãy pha một ấm trà túi lọc hoặc lục trà, chuẩn bị thêm nước lọc* và bật chế độ không làm phiền (DND) nhé!"
        else:
            msg += "Vui lòng chuẩn bị sẵn sàng."

        # Add inline buttons for quick actions
        msg += "\n\n[BUTTON:✅ Bắt đầu ngay:hb_start_now] [BUTTON:⏳ Lùi 15 phút:hb_delay_15]"

        await self._send(msg)

    # ─────────────────────────────────────
    # Job 6: Memory Sync (3:00 AM)
    # ─────────────────────────────────────
    async def memory_sync(self):
        """Sync long-term memories to BRAIN.md during off-peak hours."""
        logger.info("Running memory_sync...")
        try:
            from core.utils.memory_manager import memory_manager
            user_id = "default_user"
            memories = memory_manager.get_all_memories(user_id)

            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            brain_path = os.path.join(base_dir, "BRAIN.md")
            with open(brain_path, "w", encoding="utf-8") as f:
                f.write("# Orchesta Assistant: Transparent Memory (BRAIN.md)\n\n")
                f.write("> This file is automatically updated by the Heartbeat Engine.\n\n")
                f.write("## Long-Term Memories\n")
                if not memories:
                    f.write("No memories found.\n")
                for m in memories:
                    text = m.get('memory') or m.get('text')
                    f.write(f"- {text}\n")
            logger.info(f"Synchronized {len(memories)} memories to BRAIN.md")
        except Exception as e:
            logger.error(f"memory_sync error: {e}")

    # ─────────────────────────────────────
    # Job 7: Evolution Check (Sunday 10 AM)
    # ─────────────────────────────────────
    async def evolution_check(self):
        """Analyze BRAIN.md for potential new skills to extract (weekly)."""
        logger.info("Running evolution_check...")
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        brain_path = os.path.join(base_dir, "BRAIN.md")
        checklist_path = os.path.join(base_dir, "HEARTBEAT.md")

        if not os.path.exists(brain_path):
            return

        try:
            with open(brain_path, "r", encoding="utf-8") as f:
                content = f.read()

            from core.utils.z_research import ZResearch
            researcher = ZResearch()
            prompt = f"""
            Analyze the following distilled long-term memories and identify recurring patterns,
            complex workflows, or technical procedures that SHOULD be codified as a specialized "Skill Card".
            
            Memories:
            {content}
            
            Return a short list of potential skills (titles only) that aren't already clear.
            Format as a bulleted list. If nothing new, return "No new skills suggested."
            """

            suggestions = researcher.query(prompt)
            if "No new skills suggested" not in suggestions:
                logger.info("Evolution suggestions found.")
                with open(checklist_path, "a", encoding="utf-8") as f:
                    f.write(f"\n## Skill Evolution Suggestions ({datetime.date.today()})\n")
                    for line in suggestions.split("\n"):
                        if line.strip().startswith("-") or line.strip().startswith("*"):
                            f.write(f"- [ ] Extract skill: {line.strip()[1:].strip()}\n")

                await self._send("🧬 Evolution Probe đã gợi ý các skill mới. Kiểm tra HEARTBEAT.md.")
        except Exception as e:
            logger.error(f"evolution_check error: {e}")
