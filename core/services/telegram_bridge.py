import os
import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from core.handlers.telegram_handlers import TelegramHandlers
from core.utils.bot_logger import get_logger

class TelegramBridge:
    def __init__(self, token, user_id, log_activity_callback=None):
        self.token = token
        self.user_id = user_id
        self.log_activity = log_activity_callback
        self.logger = get_logger("telegram")
        self._graph_instance = None
        self.app = None

    def _get_graph(self):
        if self._graph_instance is None:
            self.logger.info("⏳ Building supervisor graph (lazy-load)...")
            try:
                from core.agents.supervisor import build_supervisor_graph
                self._graph_instance = build_supervisor_graph()
                self.logger.info("✅ Supervisor graph built.")
            except Exception as e:
                self.logger.error(f"❌ Failed to build supervisor graph: {e}", exc_info=True)
                raise
        return self._graph_instance

    async def run(self):
        if not self.token:
            self.logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bridge disabled.")
            return

        handlers = TelegramHandlers(self.user_id, self.logger, self._get_graph, self.log_activity)

        try:
            self.logger.info("Step 0: Building Application...")
            self.app = ApplicationBuilder().token(self.token).build()
            if not self.app:
                raise RuntimeError("Failed to build Telegram application.")

            self.logger.info("Step 0.1: Registering handlers...")
            # Command Handlers
            self.app.add_handler(CommandHandler("start", handlers.handle_help))
            self.app.add_handler(CommandHandler("help", handlers.handle_help))
            self.app.add_handler(CommandHandler("calorie", handlers.handle_calorie))
            self.app.add_handler(CommandHandler("log_meal", handlers.handle_log_meal))
            self.app.add_handler(CommandHandler("task", handlers.handle_add_task))
            self.app.add_handler(CommandHandler("tasks", handlers.handle_tasks))
            self.app.add_handler(CommandHandler("done", handlers.handle_done))
            self.app.add_handler(CommandHandler("status", handlers.handle_status))
            self.app.add_handler(CommandHandler("metrics", handlers.handle_metrics))
            self.app.add_handler(CommandHandler("usage", handlers.handle_usage))
            self.app.add_handler(CommandHandler("baocao_api", handlers.handle_usage))
            self.app.add_handler(CommandHandler("myschedule", handlers.handle_myschedule))
            self.app.add_handler(CommandHandler("sync", handlers.handle_sync))
            self.app.add_handler(CommandHandler("restart", handlers.handle_restart))
            self.app.add_handler(CommandHandler("sync_cowork", handlers.handle_sync_cowork))
            self.app.add_handler(CommandHandler("night_add", handlers.handle_night_add))
            self.app.add_handler(CommandHandler("toggle", handlers.handle_toggle))
            self.app.add_handler(CommandHandler("trend", handlers.handle_trend))
            self.app.add_handler(CommandHandler("kol", handlers.handle_kol))
            self.app.add_handler(CommandHandler("today", handlers.handle_today))
            self.app.add_handler(CommandHandler("checkmail", handlers.handle_checkmail))
            self.app.add_handler(CommandHandler("soanbai", handlers.handle_soanbai))
            self.app.add_handler(CommandHandler("colab", handlers.handle_colab))
            self.app.add_handler(CommandHandler("searchdrive", handlers.handle_searchdrive))
            self.app.add_handler(CommandHandler("ping", handlers.ping_command))
            self.app.add_handler(CommandHandler("homework", handlers.handle_homework))
            
            # Message Handlers
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
            self.app.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo))
            self.app.add_handler(MessageHandler(filters.VOICE, handlers.handle_voice))
            self.app.add_handler(CallbackQueryHandler(handlers.handle_callback))

            self.logger.info("Step 1: Initializing Application...")
            await self.app.initialize()
            
            self.logger.info("Step 1.5: Registering commands with BotFather...")
            await handlers.set_my_commands(self.app.bot)

            self.logger.info("Step 2: Starting Application...")
            await self.app.start()
            
            self.logger.info("Step 3: Starting Polling...")
            await self.app.updater.start_polling(drop_pending_updates=True)
            self.logger.info("✅ Telegram polling started.")

            await asyncio.Event().wait()
        except Exception as e:
            self.logger.error(f"❌ Telegram setup failed: {e}", exc_info=True)
            raise
