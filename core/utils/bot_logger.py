"""
BotLogger: Centralized structured logging for the Orchesta bot.

Replaces scattered print() calls with proper Python logging:
  - JSON-formatted file logs with daily rotation
  - Colored console output
  - Critical error forwarding to Telegram
"""
import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from typing import Optional


# ─── JSON Formatter ────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    """Outputs log records as JSON lines for easy parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


# ─── Colored Console Formatter ─────────────────────────────────
class ColoredFormatter(logging.Formatter):
    """Colored output for console — makes logs visually scannable."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET
        # Emoji prefixes for quick scanning
        emoji = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🔥",
        }.get(record.levelname, "")

        timestamp = datetime.now().strftime("%H:%M:%S")
        return (
            f"{color}{emoji} [{timestamp}] [{record.name}] "
            f"{record.getMessage()}{reset}"
        )


# ─── Telegram Alert Handler ───────────────────────────────────
class TelegramAlertHandler(logging.Handler):
    """
    Sends CRITICAL and ERROR logs to Telegram.
    Uses a cooldown to avoid spamming.
    """

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self._last_sent = 0
        self._cooldown_seconds = 60  # Min 1 minute between alerts

    def emit(self, record: logging.LogRecord):
        import time
        now = time.time()
        if now - self._last_sent < self._cooldown_seconds:
            return

        try:
            import asyncio
            from core.services.telegram_service import telegram_service

            message = (
                f"🔥 *{record.levelname}*\n"
                f"📍 `{record.name}:{record.funcName}:{record.lineno}`\n"
                f"💬 {record.getMessage()[:500]}"
            )

            # Try to send asynchronously if we're in an event loop
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(telegram_service.send_message(message, parse_mode="Markdown"))
            except RuntimeError:
                # No running loop — run synchronously
                asyncio.run(telegram_service.send_message(message, parse_mode="Markdown"))

            self._last_sent = now
        except Exception:
            pass  # Never let logging errors crash the bot


# ─── Logger Factory ────────────────────────────────────────────
_initialized = False


def _ensure_setup():
    """Initialize logging infrastructure once."""
    global _initialized
    if _initialized:
        return

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    log_dir = os.path.join(root_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "orchesta_bot.log")

    # Root logger config
    root_logger = logging.getLogger("orchesta")
    root_logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers on reimport
    if root_logger.handlers:
        _initialized = True
        return

    # 1. File Handler — JSON, daily rotation, 7-day retention
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # 2. Console Handler — Colored
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)

    # 3. Telegram Alert Handler — ERROR+ only
    try:
        tg_handler = TelegramAlertHandler()
        root_logger.addHandler(tg_handler)
    except Exception:
        pass

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger under the 'orchesta' namespace.

    Usage:
        from core.utils.bot_logger import get_logger
        logger = get_logger("telegram")
        logger.info("Bot started")
        logger.error("Something failed", exc_info=True)
    """
    _ensure_setup()
    return logging.getLogger(f"orchesta.{name}")
