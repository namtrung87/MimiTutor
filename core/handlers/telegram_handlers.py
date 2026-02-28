import os
import sys
import json
import time
import asyncio
import tempfile
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

try:
    from langchain_core.messages import HumanMessage
except ImportError:
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content

from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import ContextTypes

from core.utils.bot_logger import get_logger
from core.utils.feature_flags import feature_flags
from core.services.conversation_store import conversation_store
from core.utils.input_sanitizer import sanitize_user_input

class TelegramHandlers:
    def __init__(self, user_id: str, tg_logger, get_graph_func, log_activity_func):
        self.user_id = str(user_id)
        self.tg_logger = tg_logger
        self.get_graph = get_graph_func
        self.log_activity = log_activity_func

    def get_main_keyboard(self):
        keyboard = [
            ["📝 Tasks", "📊 Status"],
            ["🍎 Dinh dưỡng", "📡 Xu hướng"],
            ["🧠 AI Chat", "🎙️ Voice"],
            ["🎮 Gamification", "📖 Trợ giúp"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🚀 *Orchesta Proactive Assistant is LIVE!*\n\nChọn một chức năng bên dưới hoặc gửi lệnh để tương tác.",
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_markup=self.get_main_keyboard()
        )

    async def commute_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick toggle for Commute Mode."""
        await update.message.reply_text(
            "🚌 *COMMUTE MODE ACTIVE*\n\nChọn chế độ:\n1. 💤 /sleep - Passive Recovery\n2. 🎮 /game - Meta-Automation\n3. 🎙️ Gửi Voice - Micro-Dev Insight",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not update.message or (not update.message.text and not update.message.caption):
                return
            
            user_id_str = str(update.message.from_user.id)
            if user_id_str != self.user_id:
                return

            from langchain_core.messages import HumanMessage
            
            original_text = update.message.text or update.message.caption or ""
            user_input = sanitize_user_input(unicodedata.normalize('NFC', original_text))
            self.tg_logger.info(f"DEBUG: Received message: '{user_input}'")
            
            # Detect Approval Flow
            if user_input.strip().lower() in ["chốt", "chốt lịch", "ok chốt"]:
                from core.services.scheduler_state import scheduler_state
                now = datetime.now()
                target_date = now.date()
                if now.hour >= 20: 
                    target_date = (now + timedelta(days=1)).date()
                    
                await scheduler_state.confirm_all(target_date.isoformat())
                await update.message.reply_text(f"✅ Đã chốt lịch cho ngày {target_date.isoformat()}! Tôi sẽ nhắc nhở anh đúng giờ.")
                return

            # Button Handlers
            if "Dinh dưỡng" in user_input:
                await self.handle_calorie(update, context)
                return
            elif user_input == "📝 Tasks":
                await self.handle_tasks(update, context)
                return
            elif user_input == "📊 Status":
                await self.handle_status(update, context)
                return
            elif user_input == "🧠 AI Chat":
                await update.message.reply_text("Vui lòng nhập câu hỏi để chat với AI.")
                return
            elif user_input == "🎙️ Voice":
                await update.message.reply_text("Vui lòng gửi tin nhắn thoại (Voice Message) để sử dụng chức năng này.")
                return
            elif user_input == "🎮 Gamification":
                msg = "🎮 *Gamification Commands:*\n- `/lore <từ khóa>`: Tạo cốt truyện\n- `/pixel <mô tả>`: Gợi ý ảnh pixel\n- `/post <chủ đề>`: Xây dựng bài viết chuẩn Gameducator\n- `/trend`: Xem xu hướng AI/Finance"
                await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
                return
            elif user_input == "📡 Xu hướng":
                await self.handle_trend(update, context)
                return
            elif user_input == "📖 Trợ giúp":
                await self.handle_help(update, context)
                return

            self.tg_logger.info(f"Telegram ← {user_input}")
            self.log_activity("telegram", f"📱 {user_input}", direction="in")

            # Save user message
            await conversation_store.add_message(self.user_id, "user", user_input)
            
            # Get conversation context
            conv_context = await conversation_store.get_context_string(self.user_id, max_chars=2000)

            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "user_id": self.user_id,
                "retry_count": 0,
                "is_valid": True,
                "conversation_context": conv_context,
            }

            _start_ts = time.time()
            self.tg_logger.info(f"Starting graph invocation for: {user_input[:20]}...")
            status_msg = await update.message.reply_text("⏳ Đang xử lý...")
            
            graph = self.get_graph()
            if not graph:
                await status_msg.edit_text("❌ Hệ thống đang khởi tạo bộ não, vui lòng thử lại sau.")
                return

            result = await asyncio.wait_for(graph.ainvoke(initial_state), timeout=180.0)
            self.tg_logger.info(f"Graph invocation completed for: {user_input[:20]}")

            final_answer = ""
            routing_cat = result.get("routing_category", None)
            if result.get("messages"):
                for m in reversed(result["messages"]):
                    msg_str = m.content if hasattr(m, "content") else str(m)
                    if any(msg_str.startswith(p) for p in ["System:", "Critic:", "Intel Agent:"]):
                        continue
                    final_answer = msg_str
                    break

            if not final_answer:
                final_answer = "Đã xử lý nhưng không có phản hồi cụ thể."
            
            if isinstance(final_answer, str) and final_answer.startswith("ERROR:"):
                 final_answer = "Xin lỗi, hệ thống AI đang gặp sự cố kỹ thuật. Vui lòng thử lại sau."

            for prefix in ["Scholar Agent: ", "Learning Agent: ", "Coding Crew: ", "Tech Agent: ", "Executive Ops: ", "Wellness Coach: "]:
                if final_answer.startswith(prefix):
                    final_answer = final_answer[len(prefix):]
                    break

            response_time_ms = int((time.time() - _start_ts) * 1000)
            await conversation_store.add_message(self.user_id, "bot", final_answer[:500], routing_category=routing_cat, response_time_ms=response_time_ms)
            self.log_activity("telegram", f"🤖 {final_answer[:200]}", direction="out")

            try: await status_msg.delete()
            except: pass

            if len(final_answer) > 4000:
                chunks = [final_answer[i:i+4000] for i in range(0, len(final_answer), 4000)]
                for chunk in chunks:
                    try: await update.message.reply_text(chunk, parse_mode=constants.ParseMode.MARKDOWN)
                    except: await update.message.reply_text(chunk)
            else:
                try: await update.message.reply_text(final_answer, parse_mode=constants.ParseMode.MARKDOWN)
                except: await update.message.reply_text(final_answer)

        except asyncio.TimeoutError:
            self.tg_logger.warning("Telegram Timeout (180s)")
            await update.message.reply_text("⏱️ Timeout sau 180 giây. Server đang quá tải, vui lòng thử lại.")
            self.log_activity("telegram", "⏱️ Timeout", direction="out")
        except Exception as e:
            self.tg_logger.error(f"Telegram Error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Lỗi: {str(e)[:200]}")
            self.log_activity("telegram", f"❌ Error: {str(e)[:100]}", direction="out")

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id:
            return
        
        status_msg = await update.message.reply_text("🎙️ Đang nghe và chuyển thành văn bản...")
        self.log_activity("telegram", "🎙️ [Voice Message]", direction="in")

        try:
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            tmp_path = os.path.join(tempfile.gettempdir(), f"voice_{update.message.voice.file_id}.ogg")
            await voice_file.download_to_drive(tmp_path)

            from core.utils.multimodal_extractor import MultimodalExtractor
            extractor = MultimodalExtractor()
            transcript = await asyncio.to_thread(extractor.process_file, tmp_path, mime_type="audio/ogg")

            try: os.remove(tmp_path)
            except: pass

            if not transcript or transcript.startswith("[Error"):
                await status_msg.edit_text(f"❌ Không thể nhận dạng giọng nói: {transcript}")
                return

            await status_msg.edit_text(f"📝 *Transcript:*\n{transcript[:500]}", parse_mode=constants.ParseMode.MARKDOWN)
            await conversation_store.add_message(self.user_id, "user", f"[Voice] {transcript}")

            initial_state = {
                "messages": [transcript],
                "user_id": self.user_id,
                "retry_count": 0,
                "is_valid": True,
            }
            
            result = await asyncio.wait_for(self.get_graph().ainvoke(initial_state), timeout=120.0)
            final_answer = ""
            if result.get("messages"):
                for m in reversed(result["messages"]):
                    msg_str = str(m.content if hasattr(m, "content") else m)
                    if msg_str.startswith(("System:", "Critic:", "Intel Agent:")):
                        continue
                    final_answer = msg_str
                    break
            
            if final_answer:
                await conversation_store.add_message(self.user_id, "bot", final_answer[:500])
                try: await update.message.reply_text(final_answer, parse_mode=constants.ParseMode.MARKDOWN)
                except: await update.message.reply_text(final_answer)
            else:
                await update.message.reply_text("✅ Đã xử lý voice nhưng không có phản hồi cụ thể.")
            self.log_activity("telegram", f"🤖 Voice processed", direction="out")
        except Exception as e:
            self.tg_logger.error(f"Voice processing error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Lỗi xử lý voice: {str(e)[:200]}")

    async def handle_lore(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        desc = " ".join(context.args)
        if desc:
            from core.utils.llm_manager import LLMManager
            llm = LLMManager()
            await update.message.reply_text("⏳ Đang sáng tạo Lore...", parse_mode=constants.ParseMode.MARKDOWN)
            res = await asyncio.to_thread(llm.query, f"Bạn là chuyên gia thiết kế cốt truyện game. Hãy viết một đoạn lore ngắn, dark, sâu sắc về: {desc}", complexity="L2", domain="creative")
            await update.message.reply_text(res)
        else:
            await update.message.reply_text("Thiếu thông tin: /lore <keyword>")

    async def handle_pixel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        desc = " ".join(context.args)
        if desc:
            from core.utils.llm_manager import LLMManager
            llm = LLMManager()
            await update.message.reply_text("⏳ Đang mường tượng Pixel Art...", parse_mode=constants.ParseMode.MARKDOWN)
            res = await asyncio.to_thread(llm.query, f"Bạn là họa sĩ Pixel Art. Hãy mô tả chi tiết prompt để hệ thống tạo ảnh (DALL-E) cho ý tưởng này: {desc}", complexity="L2", domain="creative")
            await update.message.reply_text(res)
        else:
            await update.message.reply_text("Thiếu thông tin: /pixel <keyword>")

    async def handle_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        desc = " ".join(context.args)
        if desc:
            from core.utils.llm_manager import LLMManager
            llm = LLMManager()
            await update.message.reply_text("⏳ Đang thiết kế bài Post...", parse_mode=constants.ParseMode.MARKDOWN)
            res = await asyncio.to_thread(llm.query, f"Bạn là một Gameducator và System Architect. Hãy viết một bài post Facebook/LinkedIn năng lượng cao, đầy tính ẩn dụ, về chủ đề: {desc}", complexity="L2", domain="creative")
            await update.message.reply_text(res)
        else:
            await update.message.reply_text("Thiếu thông tin: /post <chủ đề>")

    async def handle_trend(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        status_msg = await update.message.reply_text("📡 Đang quét các nguồn KOL và tổng hợp xu hướng AI/Finance...")
        try:
            from core.agents.trendscout_agent import TrendScoutAgent
            agent = TrendScoutAgent()
            briefing = await asyncio.to_thread(agent.generate_daily_briefing)
            if briefing and len(briefing) > 50:
                await status_msg.delete()
                for i in range(0, len(briefing), 4000):
                    await update.message.reply_text(briefing[i:i+4000], parse_mode=constants.ParseMode.MARKDOWN)
            else:
                await status_msg.edit_text("📡 TrendScout: Không tìm thấy dữ liệu mới.")
        except Exception as e:
            self.tg_logger.error(f"Trend error: {e}")
            await status_msg.edit_text(f"❌ Lỗi trend: {str(e)[:100]}")

    async def handle_kol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        domain = context.args[0].lower() if context.args else "list"
        from core.agents.trendscout_agent import TrendScoutAgent
        agent = TrendScoutAgent()
        if domain == "list":
            domains = agent.list_domains()
            domain_list = "\n".join([f"• `{d['key']}`: {d['label']} ({d['source_count']} nguồn)" for d in domains])
            await update.message.reply_text(f"📋 **Các domain KOL đang theo dõi:**\n\n{domain_list}\n\n*HD: Gõ `/kol <domain>` để xem báo cáo riêng.*", parse_mode=constants.ParseMode.MARKDOWN)
            return
        status_msg = await update.message.reply_text(f"📊 Đang tổng hợp báo cáo KOL cho: `{domain}`...", parse_mode=constants.ParseMode.MARKDOWN)
        try:
            report = await asyncio.to_thread(agent.get_domain_summary, domain)
            await status_msg.delete()
            await update.message.reply_text(report, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception as e:
            await status_msg.edit_text(f"❌ Lỗi: {str(e)[:100]}")

    async def handle_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        from core.services.scheduler_state import LOCAL_TZ
        today_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(BASE_DIR, "11_Personal_Learning", "summaries", f"briefing_{today_str}.md")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f: content = f.read()
            for i in range(0, len(content), 4000):
                await update.message.reply_text(content[i:i+4000], parse_mode=constants.ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("📅 Hôm nay chưa có báo cáo TrendScout. Gõ `/trend` để tạo mới!")

    async def handle_calorie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        from core.services.scheduler_state import scheduler_state
        today = await scheduler_state.get_todays_calories()
        msg = f"🍎 **Nutrition Tracker Today**\n\n🎯 Mục tiêu: `{today['goal']}` kcal\n✅ Tổng nạp: `{today['total_calories']}` kcal\n🔥 Còn lại: `{today['remaining']}` kcal\n\n📝 **Bữa ăn:**\n"
        if today['meals']:
            for m in today['meals']:
                time_str = m['time'][11:16] if m.get('time') else "??"
                msg += f"- `{time_str}`: {m['desc']} ({m['calories']} kcal)\n"
        else: msg += "- Chưa có bữa ăn nào được ghi nhận."
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

    async def handle_add_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        desc = " ".join(context.args)
        if desc:
            from core.utils.task_manager import task_manager
            task_id = await task_manager.add_task(self.user_id, desc)
            await update.message.reply_text(f"✅ Đã thêm task #{task_id}: {desc}")
        else:
            await update.message.reply_text("Vui lòng nhập nội dung: /task <nội dung>")

    async def handle_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        from core.utils.task_manager import task_manager
        tasks = await task_manager.get_pending_tasks(self.user_id)
        if not tasks:
            await update.message.reply_text("✅ Anh không có task nào đang chờ!")
        else:
            msg = "📋 *Các task hiện tại:*\n"
            for t in tasks:
                time_str = f" (lúc {t['scheduled_time'][11:16]})" if t.get('scheduled_time') else ""
                msg += f"- `#{t['id']}`: {t['desc']}{time_str}\n"
            msg += "\nDùng `/done <id>` để hoàn thành."
            await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

    async def handle_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        if not context.args:
            await update.message.reply_text("Vui lòng nhập ID: /done <id>")
            return
        try:
            task_id = int(context.args[0])
            from core.utils.task_manager import task_manager
            if await task_manager.complete_task(self.user_id, task_id):
                await update.message.reply_text(f"🎉 Đã hoàn thành task #{task_id}!")
            else:
                await update.message.reply_text(f"❌ Không tìm thấy task #{task_id} đang chờ.")
        except:
            await update.message.reply_text("ID không hợp lệ.")

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        import subprocess
        await update.message.reply_text("⏳ Đang lấy thông tin hệ thống...")
        try:
            result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5, creationflags=0x08000000)
            data = json.loads(result.stdout)
            msg = "📊 *System Status*\n\n"
            for proc in data:
                name = proc.get("name")
                status = proc.get("pm2_env", {}).get("status", "unknown")
                mem = proc.get("monit", {}).get("memory", 0) / (1024*1024)
                msg += f"🔹 *{name}*: {status} ({mem:.1f} MB)\n"
            await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi khi lấy PM2 status: {e}")

    async def handle_sync_cowork(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        import subprocess
        await update.message.reply_text("⏳ Đang đồng bộ ngữ cảnh với Claude Cowork...")
        try:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            script_path = os.path.join(BASE_DIR, "core", "scripts", "cowork_bridge.py")
            subprocess.run([sys.executable, script_path, "--sync"], check=True, creationflags=0x08000000)
            await update.message.reply_text("✅ Đã đồng bộ thành công! Bạn có thể tiếp tục trao đổi với Claude.")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi đồng bộ: {e}")

    async def handle_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        ALLOWED_RESTART_APPS = {"orchesta-launcher", "mimi-parent-console", "orchesta-dashboard"}
        if not context.args:
            allowed = ', '.join(f'`{a}`' for a in ALLOWED_RESTART_APPS)
            await update.message.reply_text(f"Vui lòng nhập tên app: /restart <tên>\nApp được phép: {allowed}", parse_mode=constants.ParseMode.MARKDOWN)
            return
        app_name = context.args[0]
        if app_name not in ALLOWED_RESTART_APPS:
            allowed = ', '.join(f'`{a}`' for a in ALLOWED_RESTART_APPS)
            await update.message.reply_text(f"❌ App `{app_name}` không hợp lệ.\nApp được phép: {allowed}", parse_mode=constants.ParseMode.MARKDOWN)
            return
        await update.message.reply_text(f"⏳ Đang restart `{app_name}`...", parse_mode=constants.ParseMode.MARKDOWN)
        import subprocess
        try:
            subprocess.run(["pm2", "restart", app_name], capture_output=True, text=True, timeout=10, creationflags=0x08000000)
            await update.message.reply_text(f"✅ Đã gửi lệnh restart cho `{app_name}`", parse_mode=constants.ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi khi restart: {e}")

    async def handle_night_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        if len(context.args) < 1:
            help_msg = "🌙 *Night Shift — Thêm công việc ca đêm*\n\nSử dụng: `/night_add <handler>`\n\n**Handlers:**\n• `code_audit`\n• `story_expansion`\n• `deep_research <topic>`\n• `deep_memory_consolidation`\n• `auto_content_pipeline`\n• `weekly_calendar_gen`\n• `wellness_digest`"
            await update.message.reply_text(help_msg, parse_mode=constants.ParseMode.MARKDOWN)
            return
        handler = context.args[0]
        from core.services.night_shift import night_shift
        HANDLER_MAP = {
            'code_audit': ('code_audit_and_test', {"target_dir": "core/services"}),
            'story_expansion': ('story_expansion', {"game": "Cost of Success", "type": "dialogue", "context": "Gặp gỡ The Auditor trong hẻm tối", "count": 3}),
            'deep_research': ('deep_research', {"topic": " ".join(context.args[1:]) if len(context.args) > 1 else "Xu hướng AI 2026", "source_url_or_path": "Mocked source"}),
            'deep_memory_consolidation': ('deep_memory_consolidation', {"user_id": self.user_id}),
            'auto_content_pipeline': ('auto_content_pipeline', {}),
            'weekly_calendar_gen': ('weekly_calendar_gen', {"week_offset": 1}),
            'wellness_digest': ('wellness_digest', {"period": "weekly"}),
        }
        if handler not in HANDLER_MAP:
            await update.message.reply_text(f"❌ Unknown handler: `{handler}`")
            return
        registered_name, payload = HANDLER_MAP[handler]
        job_id = await night_shift.add_job(f"Telegram Job ({handler})", registered_name, payload)
        await update.message.reply_text(f"✅ Đã thêm Night Job `#{job_id}`.")

    async def handle_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        if not context.args or len(context.args) < 2:
            flags = feature_flags.get_all()
            msg = "⚙️ *Feature Toggles*\n\n"
            for f, enabled in flags.items(): msg += f"{'✅' if enabled else '❌'} `{f}`\n"
            msg += "\nSử dụng: `/toggle <feature> <on|off>`"
            await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
            return
        feature, state = context.args[0], context.args[1].lower()
        if feature not in feature_flags.get_all():
            await update.message.reply_text(f"❌ Unknown feature: `{feature}`")
            return
        enabled = state in ["on", "true", "1", "enable"]
        feature_flags.set_feature(feature, enabled)
        await update.message.reply_text(f"{'✅ Enabled' if enabled else '🚫 Disabled'}: `{feature}`")
        self.log_activity("telegram", f"⚙️ Feature '{feature}' set to {enabled}", direction="in")

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📖 *Orchesta Bot — Danh sách lệnh*\n\n"
            "*💬 Trò chuyện:*\nTin nhắn, Ảnh, Tài liệu, Voice → Tự động xử lý\n\n"
            "*🍽️ Dinh Dưỡng:*\n`/log_meal <món ăn>`\n\n"
            "*📋 Task Management:*\n`/task`, `/tasks`, `/done <id>`\n\n"
            "*🎮 Creative:*\n`/lore`, `/pixel`, `/post`, `/trend`\n\n"
            "*🔧 DevOps:*\n`/status`, `/restart`, `/usage`, `/metrics`, `/night_add`, `/toggle`\n"
        )
        await update.message.reply_text(help_text, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=self.get_main_keyboard())

    async def handle_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        stats = await conversation_store.get_stats(self.user_id)
        msg = f"📊 *Bot Metrics*\n\n💬 Hôm nay: {stats['today_messages']}\n📚 Tổng: {stats['total_messages']}\n"
        if stats['avg_response_time_ms']: msg += f"⏱️ Phản hồi TB: {stats['avg_response_time_ms']}ms\n"
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

    async def handle_usage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        stats_file = Path("usage_stats.json")
        if not stats_file.exists():
            await update.message.reply_text("❌ Không tìm thấy usage_stats.json")
            return
        try:
            with open(stats_file, "r") as f: stats = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in stats:
                await update.message.reply_text(f"📊 Báo cáo ngày {today}: Chưa có dữ liệu.")
                return
            day_stats = stats[today]
            msg = f"📊 *GEMINI API USAGE - {today}*\n💰 **Tổng chi phí:** `{day_stats.get('total_cost_vnd', 0):.1f} VND`"
            await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}")

    async def handle_checkmail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        from core.agents.gmail_executive_agent import GmailExecutiveAgent
        await update.message.reply_text("📧 Đang check Gmail...")
        agent = GmailExecutiveAgent()
        await agent.run_daily_check()

    async def handle_soanbai(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        topic = " ".join(context.args)
        if not topic:
            await update.message.reply_text("💡 Nhập chủ đề: `/soanbai <topic>`")
            return
        await update.message.reply_text(f"📚 Đang tạo Slide cho: {topic}...")
        from core.agents.drive_educator_agent import DriveEducatorAgent
        agent = DriveEducatorAgent()
        url = await asyncio.to_thread(agent.generate_session_materials, topic)
        await update.message.reply_text(f"✅ Xong: {url}" if url else "❌ Lỗi Drive.")

    async def handle_colab(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        nb_name = " ".join(context.args)
        if not nb_name:
            await update.message.reply_text("💡 Nhập tên notebook: `/colab <name>`")
            return
        await update.message.reply_text(f"🔄 Đang chạy Colab: {nb_name}...")
        from core.utils.colab_automator import ColabAutomator
        automator = ColabAutomator()
        result = await asyncio.to_thread(automator.run_notebook, nb_name)
        await update.message.reply_text(f"✅ Thành công" if result['status'] == 'success' else f"❌ Lỗi: {result.get('error')}")

    async def handle_searchdrive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("💡 Nhập từ khóa: `/searchdrive <query>`")
            return
        await update.message.reply_text(f"🔍 Đang tìm Drive cho: {query}...")
        from core.utils.google_researcher import GoogleResearcher
        researcher = GoogleResearcher()
        summary = await asyncio.to_thread(researcher.research_topic_in_drive, query)
        await update.message.reply_text(summary[:4000] if summary else "Không tìm thấy.")

    async def handle_myschedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        from core.services.scheduler_state import scheduler_state
        schedule = await scheduler_state.load_schedule()
        if not schedule:
            await update.message.reply_text("📅 Chưa có lịch trình.")
            return
        msg = "📅 *Lịch trình hôm nay:*\n"
        for item in schedule:
            msg += f"- `{item['start_time'][11:16] if 'T' in item['start_time'] else 'All Day'}`: {item['summary']}\n"
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

    async def handle_sync(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        from core.services.heartbeat_service import HeartbeatService
        await update.message.reply_text("🔄 Đang đồng bộ Google Calendar...")
        hb = HeartbeatService(context.bot, self.user_id)
        await hb.morning_sync()

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        status_msg = await update.message.reply_text("🖼️ Đang phân tích ảnh...")
        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            tmp_path = os.path.join(tempfile.gettempdir(), f"photo_{photo.file_id}.jpg")
            await file.download_to_drive(tmp_path)
            from core.utils.multimodal_extractor import MultimodalExtractor
            extractor = MultimodalExtractor()
            analysis = await asyncio.to_thread(extractor.process_file, tmp_path, mime_type="image/jpeg")
            try: os.remove(tmp_path)
            except: pass
            await conversation_store.add_message(self.user_id, "user", f"[Photo] {update.message.caption or 'image'}")
            await status_msg.edit_text(analysis[:4000], parse_mode=constants.ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}")

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        doc = update.message.document
        status_msg = await update.message.reply_text(f"📄 Đang xử lý `{doc.file_name}`...")
        try:
            file = await context.bot.get_file(doc.file_id)
            tmp_path = os.path.join(tempfile.gettempdir(), doc.file_name)
            await file.download_to_drive(tmp_path)
            from core.utils.multimodal_extractor import MultimodalExtractor
            extractor = MultimodalExtractor()
            content = await asyncio.to_thread(extractor.process_file, tmp_path)
            try: os.remove(tmp_path)
            except: pass
            from core.utils.llm_manager import LLMManager
            llm = LLMManager()
            summary = await asyncio.to_thread(llm.query, f"Tóm tắt: {content[:8000]}", complexity="L2")
            await status_msg.edit_text(f"📄 *Tóm tắt:*\n\n{summary[:3800]}", parse_mode=constants.ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}")

    async def handle_log_meal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        if not context.args:
            await update.message.reply_text("🍽️ Nhập món: `/log_meal <món>`")
            return
        meal_desc = " ".join(context.args)
        status_msg = await update.message.reply_text(f"⏳ Đang tính Calo cho: {meal_desc}...")
        try:
            from core.utils.llm_manager import LLMManager
            import re
            llm = LLMManager()
            prompt = f"Estimate calories for: {meal_desc}. Respond ONLY with an integer."
            cal_str = await asyncio.to_thread(llm.query, prompt, complexity="L2")
            cal = int(re.findall(r'\d+', cal_str)[0])
            from core.services.scheduler_state import scheduler_state
            await scheduler_state.log_meal_exact(meal_desc, cal)
            today_data = await scheduler_state.get_todays_calories()
            await status_msg.edit_text(f"✅ {cal} kcal cho {meal_desc}. Tổng: {today_data['total_calories']} kcal.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Lỗi: {e}")

    async def handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.message.from_user.id) != self.user_id: return
        await conversation_store.clear_user(self.user_id)
        await update.message.reply_text("🗑️ Đã xóa lịch sử hội thoại.")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        if data == "confirm_schedule":
            from core.services.scheduler_state import scheduler_state
            await scheduler_state.confirm_all()
            await query.edit_message_text("✅ Đã chốt lịch!")
        elif data.startswith("done_"):
            task_id = int(data.split("_")[1])
            from core.utils.task_manager import task_manager
            if await task_manager.complete_task(self.user_id, task_id):
                await query.edit_message_text(f"🎉 Đã hoàn thành task #{task_id}!")
            else:
                await query.edit_message_text(f"❌ Không tìm thấy task #{task_id}.")
        elif data.startswith("snooze_"):
            task_id = data.split("_")[1]
            from core.services.scheduler_state import scheduler_state
            await scheduler_state.update_task(task_id, {"reminded": False})
            await query.edit_message_text(f"⏰ Sẽ nhắc lại sau.")

    async def handle_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📚 Homework Tracker: Đang phát triển.")

    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Pong! Bot is alive.")

    async def set_my_commands(self, bot):
        """Register all commands with BotFather."""
        commands = [
            BotCommand("start", "Khởi động bot"),
            BotCommand("help", "Xem danh sách lệnh"),
            BotCommand("task", "Thêm task mới"),
            BotCommand("tasks", "Xem task đang chờ"),
            BotCommand("done", "Hoàn thành task"),
            BotCommand("status", "Xem trạng thái hệ thống"),
            BotCommand("usage", "Báo cáo chi phí API Gemini"),
            BotCommand("baocao_api", "Báo cáo chi phí API Gemini (alias)"),
            BotCommand("metrics", "Thống kê bot"),
            BotCommand("commute", "Commute Mode"),
            BotCommand("trend", "Xu hướng AI/Finance"),
            BotCommand("lore", "Tạo game lore"),
            BotCommand("pixel", "Gợi ý Pixel Art"),
            BotCommand("post", "Viết bài social media"),
            BotCommand("restart", "Restart PM2 app"),
            BotCommand("night_add", "Thêm Night Job"),
            BotCommand("toggle", "Tắt/bật tính năng"),
            BotCommand("log_meal", "Ghi nhận bữa ăn + Calo"),
            BotCommand("clear", "Xóa lịch sử hội thoại"),
            BotCommand("kol", "Báo cáo KOL theo domain"),
            BotCommand("today", "Xem báo cáo xu hướng hôm nay"),
            BotCommand("calorie", "Xem tổng calo hôm nay"),
            BotCommand("checkmail", "Check thư rác/mới nhất"),
            BotCommand("soanbai", "Auto Gamma từ Google Drive"),
            BotCommand("colab", "Khởi động Colab Script"),
            BotCommand("searchdrive", "Tìm kiếm và RAG Drive"),
            BotCommand("schedule", "Đặt lịch Calendar (NLP)"),
            BotCommand("myschedule", "Xem lịch trình hôm nay"),
            BotCommand("sync", "Đồng bộ lịch Google Calendar"),
            BotCommand("homework", "Ghi nhận & nhắc bài tập Bông Bông (19:30)"),
        ]
        try:
            await bot.set_my_commands(commands)
            self.tg_logger.info(f"✅ Registered {len(commands)} commands with BotFather")
        except Exception as e:
            self.tg_logger.warning(f"Failed to register commands: {e}")
