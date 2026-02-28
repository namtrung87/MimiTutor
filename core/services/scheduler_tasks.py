import os
import logging
import datetime
import json
import asyncio
from pathlib import Path
from zoneinfo import ZoneInfo
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.services.heartbeat_service import HeartbeatService
from core.services.scheduler_state import scheduler_state
from core.utils.task_manager import task_manager
from core.utils.feature_flags import feature_flags
from core.services.conversation_store import conversation_store
from core.utils.llm_manager import LLMManager
from core.utils.bot_logger import get_logger
logger = get_logger("scheduler")

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

class SchedulerTasks:
    def __init__(self, bot: Bot, user_id: str):
        self.bot = bot
        self.user_id = user_id
        self.hb_service = HeartbeatService(bot, user_id)
        self.last_habit_msg_time = None

    async def send_evening_wrapup(self):
        if not feature_flags.is_enabled("evening_wrapup"):
            logger.info("Evening Wrapup skipped (disabled via feature flags)")
            return
        if not self.bot or not self.user_id: return
        msg = "🌙 *End-of-Day Wrap-up*\n\n"
        
        completed = await task_manager.get_completed_tasks_today(str(self.user_id))
        if completed:
            msg += "🎉 *Hoàn thành xuất sắc:*\n"
            for t in completed:
                msg += f"- ~{t['desc']}~\n"
        else:
            msg += "Hôm nay chưa có task nào được đánh dấu hoàn thành.\n"
            
        pending = await task_manager.get_pending_tasks(str(self.user_id))
        if pending:
            msg += "\n📝 *Còn dang dở:*\n"
            for t in pending:
                msg += f"- {t['desc']}\n"
                
        msg += "\n\n**Tech Curfew:** Đã đến lúc ngắt kết nối màn hình để chuẩn bị cho giấc ngủ sâu nhé!"
        msg += "\n\n💤 Chúc anh buổi tối thư giãn!"
        
        try:
            await self.bot.send_message(chat_id=self.user_id, text=msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Evening Wrapup Error: {e}")

    async def check_due_tasks(self):
        if not feature_flags.is_enabled("scheduler"): return
        if not self.bot or not self.user_id: return
        try:
            now = datetime.datetime.now(LOCAL_TZ)
            # 1. Manual tasks (tasks.db)
            due_tasks = await task_manager.get_due_tasks(str(self.user_id))
            for t in due_tasks:
                msg = f"⏰ *Nhắc việc đến giờ:*\n\n- `{t['desc']}`\n\nGõ `/done {t['id']}` sau khi hoàn thành."
                await self.bot.send_message(chat_id=self.user_id, text=msg, parse_mode=ParseMode.MARKDOWN)
                
            # 2. Planned daily schedule (daily_schedule.json)
            pending_reminders = await scheduler_state.get_pending_reminders()
            for r in pending_reminders:
                summary = r.get('summary', 'Sự kiện')
                start = r.get('start_time', '')[11:16] if 'T' in r.get('start_time', '') else r.get('start_time', '')
                msg = f"🔔 *Sắp đến giờ:* `{summary}` lúc {start}\n\n"
                
                s_lower = summary.lower()
                if "ngủ" in s_lower or "sleep" in s_lower:
                    msg += "💤 Đã đến lúc gác lại công việc, chuẩn bị vệ sinh cá nhân và đi ngủ để hồi phục năng lượng nhé!"
                elif any(word in s_lower for word in ["code", "luận án", "deep work", "nghiên cứu"]):
                    msg += "🧠 Chuẩn bị vào block làm việc tập trung. *Hãy pha một ấm trà túi lọc hoặc lục trà, chuẩn bị thêm nước lọc* và bật chế độ không làm phiền (DND) nhé!"
                elif any(word in s_lower for word in ["giảng dạy", "teaching"]):
                    msg += "🚀 Đây là giờ đi dạy, bạn nên chuẩn bị di chuyển để kịp giờ."
                elif any(word in s_lower for word in ["mma", "boxing", "gym", "tập"]):
                    msg += "👟 Đã đến lúc chuẩn bị đồ đạc và chuẩn bị đi tập rồi! *Đừng quên pha một bình nước điện giải để bù khoáng và dùng máy massage Đầu gối sau tập nhé.*"
                elif any(word in s_lower for word in ["họp", "meeting", "đối tác", "call"]):
                    msg += "💼 Sắp đến giờ họp/gặp gỡ. *Hãy thực hiện 3 lần 'Physiologic Sigh' (Hít 2 - Thở 1) để reset hệ thần kinh, giữ bình tĩnh nhé.*"
                elif any(word in s_lower for word in ["bữa", "ăn", "meal", "dinh dưỡng"]):
                    llm = LLMManager()
                    today = await scheduler_state.get_todays_calories()
                    prompt = f"""Đóng vai chuyên gia dinh dưỡng võ thuật.
Sự kiện: {summary} vào lúc {start}.
Mục tiêu: {today['goal']} calo/ngày. Đã ăn: {today['total_calories']}. Còn lại: {today['remaining']}.
Lịch sử ăn hôm nay: {json.dumps(today['meals'], ensure_ascii=False)}
Hãy viết 1 câu nhắc nhở Telegram ngắn gọn (dưới 40 chữ) gợi ý người dùng nên ăn gì/lượng bao nhiêu cho bữa này dựa trên số calo còn lại. Dùng emoji."""
                    try:
                        ai_msg = await asyncio.to_thread(llm.query, prompt, complexity="L1")
                        msg += f"🍽️ *AI Recommendation:*\n{ai_msg}"
                    except Exception:
                        msg += "Vui lòng chuẩn bị bữa ăn cân bằng."
                else:
                    msg += "Vui lòng chuẩn bị sẵn sàng."

                await self.bot.send_message(chat_id=self.user_id, text=msg, parse_mode=ParseMode.MARKDOWN)
                # Mark as reminded
                await scheduler_state.update_task(r.get('id'), {"reminded": True})
                
            # 3. Active Deep Work habits
            active_events = await scheduler_state.get_ongoing_deep_work_events()
            for event in active_events:
                await self._check_deep_work_habits(event, now)

            # 4. Hourly Posture Reset
            if now.minute == 45:
                await self._posture_reset(now)

        except Exception as e:
            logger.error(f"Due Tasks Check Error: {e}")

    async def _check_deep_work_habits(self, event, now):
        event_id = event.get('id')
        last_reminded_str = event.get('last_micro_reminded_at')
        count = event.get('micro_reminders_count', 0)

        try:
            start_time = datetime.datetime.fromisoformat(event['start_time'].replace("Z", "+00:00"))
            if start_time.tzinfo is None: start_time = start_time.replace(tzinfo=LOCAL_TZ)
            else: start_time = start_time.astimezone(LOCAL_TZ)
        except Exception: return

        minutes_since_start = (now - start_time).total_seconds() / 60
        last_reminded = datetime.datetime.fromisoformat(last_reminded_str) if last_reminded_str else None
        minutes_since_last = (now - last_reminded).total_seconds() / 60 if last_reminded else 999

        micro_msg = ""
        if minutes_since_start >= 30 and minutes_since_last >= 30:
            if 85 <= minutes_since_start <= 100:
                micro_msg = "🚶 *Micro-Break (90p Focus):* Đã đến lúc đứng dậy vươn vai 2 phút, đi lấy thêm trà/nước để làm mới não bộ nhé!"
            else:
                micro_msg = "👁️ *Quy tắc 20-20-20 (30p Focus):* Hãy nhìn xa 6m trong 20s và uống 1 ngụm nước để bảo vệ mắt và não."
        
        if micro_msg:
            if self.last_habit_msg_time and (now - self.last_habit_msg_time).total_seconds() < 1200:
                pass # Skip due to 20m silence buffer
            else:
                if "90p Focus" in micro_msg:
                    micro_msg = (
                        "🧘 *Micro-Break & Stretch (90p):* Đã đến lúc đứng dậy! Hãy thử:\n"
                        "1. **Jefferson Curl**: Cuộn người xuống sàn (30s).\n"
                        "2. **Scorpion Stretch**: Mở ngực/vai.\n"
                        "3. Đi lấy thêm trà/nước để làm mới não bộ."
                    )
                await self.bot.send_message(chat_id=self.user_id, text=micro_msg, parse_mode=ParseMode.MARKDOWN)
                self.last_habit_msg_time = now
                await scheduler_state.update_task(event_id, {
                    "last_micro_reminded_at": now.isoformat(),
                    "micro_reminders_count": count + 1
                })

    async def _posture_reset(self, now):
        if self.last_habit_msg_time and (now - self.last_habit_msg_time).total_seconds() < 1200:
            pass
        else:
            posture_msg = "🧍 *Posture Reset (Hourly):* Thẳng lưng - Thả lỏng vai - Mắt ngang màn hình nhé!"
            await self.bot.send_message(chat_id=self.user_id, text=posture_msg, parse_mode=ParseMode.MARKDOWN)
            self.last_habit_msg_time = now

    async def send_weekly_review(self):
        if not self.bot or not self.user_id: return
        try:
            stats = await conversation_store.get_stats(str(self.user_id))
            llm = LLMManager()
            summary = await asyncio.to_thread(
                llm.query,
                f"Dựa vào dữ liệu sau, viết Weekly Review ngắn gọn cho user:\n"
                f"- Tổng tin nhắn tuần này: {stats['total_messages']}\n"
                f"- Routing phân bổ: {stats['routing_distribution']}\n"
                f"- Thời gian phản hồi TB: {stats['avg_response_time_ms']}ms\n"
                f"Hãy khen ngợi, đề xuất cải thiện, và gợi ý mục tiêu tuần tới.",
                complexity="L2"
            )
            msg = f"📅 *Weekly Review*\n\n{summary}"
            await self.bot.send_message(chat_id=self.user_id, text=msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Weekly review error: {e}")

    async def maintenance(self):
        await conversation_store.prune_old(days=7)

    async def send_recovery_reminder(self):
        if not self.bot or not self.user_id: return
        msg = "💆‍♂️ *Recovery Sequence:* Đã đến lúc dùng **Súng Massage/Foam Roller** (15p) để nới lỏng cơ bắp, sau đó dùng **Máy massage Chân** (15p) để thư giãn hệ thần kinh chuẩn bị ngủ sâu nhé!"
        try:
            await self.bot.send_message(chat_id=self.user_id, text=msg, parse_mode=ParseMode.MARKDOWN)
        except Exception: pass

    async def send_midday_refresh(self):
        if not self.bot or not self.user_id: return
        msg = "👀 *Lunch Refresh:* Đừng quên dùng **Máy massage Mắt** (10p) và **Máy massage Cổ vai** để hồi phục năng lượng cho buổi chiều nhé!"
        try:
            await self.bot.send_message(chat_id=self.user_id, text=msg, parse_mode=ParseMode.MARKDOWN)
        except Exception: pass

    async def send_lunch_reminder(self):
        if not self.bot or not self.user_id: return
        try:
            today = await scheduler_state.get_todays_calories()
            if today["total_calories"] == 0:
                msg_text = "Hôm nay bạn chưa ăn sáng trên hệ thống. Trưa nay hãy nạp đủ 700-800 calo (cơm, thịt, rau) để có năng lượng tập luyện/code nhé."
            else:
                llm = LLMManager()
                prompt = f"""Đóng vai chuyên gia dinh dưỡng võ thuật cho Programmer kiêm MMA Fighter. 
Người dùng đặt mục tiêu {today['goal']} calo/ngày để giảm mỡ cắt cân chậm.
Hôm nay họ đã ăn {today['total_calories']} calo. Còn lại {today['remaining']} calo cho cả ngày.
Họ chuẩn bị ăn TRƯA. Hãy viết 1 tin nhắn Telegram ngắn gọn (dưới 80 chữ), báo cáo nhanh số năng lượng đã ăn, và đưa ra gợi ý lượng thức ăn cho mâm cơm nhà (bao nhiêu bát cơm, thịt nạc, rau) để ăn trưa sao cho vọn vẹn mà vẫn đủ dư calo cho bữa tối. Dùng emoji phù hợp. Cuối tin nhắn, HIỂN NHIÊN phải đặt một câu hỏi gợi mở để người dùng khai báo lại bữa ăn của họ (VD: "Ăn trưa xong nhớ báo lại cho tôi biết bạn đã ăn gì nhé!")."""
                msg_text = await asyncio.to_thread(llm.query, prompt, complexity="L1")
            
            final_msg = f"🍲 *Lunch Builder:*\n\n{msg_text}\n\n*(👉 Gõ `/log_meal món ăn` để hệ thống tính toán cho bữa tối)*"
            await self.bot.send_message(chat_id=self.user_id, text=final_msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Lunch Reminder Error: {e}")

    async def send_dinner_reminder(self):
        if not self.bot or not self.user_id: return
        try:
            today = await scheduler_state.get_todays_calories()
            llm = LLMManager()
            prompt = f"""Đóng vai chuyên gia dinh dưỡng võ thuật cho Programmer kiêm MMA Fighter. 
Người dùng đặt mục tiêu {today['goal']} calo/ngày để giảm mỡ.
Hôm nay họ đã ăn tổng cộng {today['total_calories']} calo (các bữa trước). Quỹ calo cho buổi TỐI còn lại: {today['remaining']} calo.
Họ chuẩn bị ăn TỐI. Hãy viết 1 tin nhắn Telegram ngắn gọn (dưới 80 chữ), báo cáo số calo đã ăn, dự báo số dư và gợi ý cách gắp đồ ăn (đặc biệt nhấn mạnh vào lượng cơm) để khít mục tiêu {today['remaining']} calo còn lại.
Dành riêng cho bữa TỐI. Giọng điệu thiết thực. Cuối tin nhắn, XIN HÃY đặt một câu hỏi thân thiện yêu cầu người dùng kể lại bữa tối của họ để đóng sổ cuối ngày."""
            msg_text = await asyncio.to_thread(llm.query, prompt, complexity="L1")
            final_msg = f"🍽️ *Dinner Builder:*\n\n{msg_text}\n\n*(👉 Gõ `/log_meal món ăn` để tôi tính toán cho sáng mai rực rỡ nhé)*"
            await self.bot.send_message(chat_id=self.user_id, text=final_msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Dinner Reminder Error: {e}")

    async def send_snack_reminder(self, snack_type: str):
        if not self.bot or not self.user_id: return
        balance = await scheduler_state.get_calorie_balance()
        msg = ""
        if snack_type == "breakfast":
            msg = "🍳 *Breakfast Protocol:*\n"
            if balance > 0:
                msg += "Tối qua nạp khá nhiều rồi, sáng nay ăn thật nhẹ nhàng thôi nhé: **1 quả Táo + 1 Sữa chua không đường** hoặc **1 muỗng Whey** là đủ! 🍏🥛"
            else:
                msg += "Sáng nay cần nạp năng lượng: **2 Trứng luộc + Sandwich trắng** để duy trì đường huyết ổn định cho block Deep Work! 🥚🍞"
        elif snack_type == "pre_workout":
            msg = "🥊 *Pre-MMA Boost:*\nMáy sắp chạy hết công suất! Hãy ăn nhẹ **1 lát Sandwich trắng + 1 nửa quả Táo** ngay bây giờ để có năng lượng bung nổ trên thảm, không lo đầy bụng! 🍞🍏"
        elif snack_type == "post_workout":
            msg = "💦 *Post-MMA Recovery:*\nTuyệt vời! Giải cơ xong thì nạp ngay **1 bình Whey Protein** hoặc **2 lòng trắng trứng luộc** để cơ bắp phục hồi tức khắc nhé! 🥤🥚"
        
        try:
            if msg:
                await self.bot.send_message(chat_id=self.user_id, text=msg, parse_mode=ParseMode.MARKDOWN)
        except Exception: pass

    async def send_trendscout(self):
        if not self.bot or not self.user_id: return
        try:
            from core.agents.trendscout_agent import TrendScoutAgent
            agent = TrendScoutAgent()
            briefing = await asyncio.to_thread(agent.generate_daily_briefing)
            if briefing and len(briefing) > 50:
                for i in range(0, len(briefing), 4000):
                    await self.bot.send_message(chat_id=self.user_id, text=briefing[i:i+4000], parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"TrendScout periodic error: {e}")

    def register_all(self, scheduler: AsyncIOScheduler):
        # Heartbeat Service Jobs
        self.hb_service.register_jobs(scheduler)
        
        # Additional Scheduler-specific Jobs
        scheduler.add_job(lambda: asyncio.create_task(self.send_snack_reminder("breakfast")), 'cron', hour=7, minute=30)
        scheduler.add_job(self.send_lunch_reminder, 'cron', hour=11, minute=30)
        scheduler.add_job(self.send_midday_refresh, 'cron', hour=12, minute=0)
        scheduler.add_job(lambda: asyncio.create_task(self.send_snack_reminder("pre_workout")), 'cron', hour=16, minute=30)
        scheduler.add_job(lambda: asyncio.create_task(self.send_snack_reminder("post_workout")), 'cron', hour=18, minute=0)
        scheduler.add_job(self.send_dinner_reminder, 'cron', hour=18, minute=30)
        scheduler.add_job(self.send_recovery_reminder, 'cron', hour=21, minute=30)
        scheduler.add_job(self.check_due_tasks, 'interval', minutes=1)
        scheduler.add_job(self.send_weekly_review, 'cron', day_of_week='mon', hour=8, minute=0)
        scheduler.add_job(self.maintenance, 'cron', hour=3, minute=0)
        
        logger.info("SchedulerTasks: All background jobs registered.")
