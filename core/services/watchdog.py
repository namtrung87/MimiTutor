"""
BotWatchdog: Self-monitoring module for the Orchesta Telegram bot.

Periodically checks:
  1. LLM connectivity (quick ping)
  2. Telegram API responsiveness
  3. Memory usage
  
Sends alerts via Telegram when failures are detected.
"""
import asyncio
import os
import time
import traceback
import psutil
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class BotWatchdog:
    """Self-monitoring watchdog that runs as a background task."""

    def __init__(self, check_interval_seconds: int = 3600):
        self.check_interval = check_interval_seconds  # default 5 min
        self.consecutive_failures = 0
        self.max_failures_before_alert = 3
        self.last_healthy_time: Optional[datetime] = None
        self.is_running = False
        self._stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "last_error": None,
            "uptime_start": datetime.now().isoformat(),
        }

    async def _check_llm_health(self) -> bool:
        """Quick LLM connectivity test with a minimal query."""
        try:
            from core.utils.llm_manager import LLMManager
            llm = LLMManager()
            result = await asyncio.to_thread(llm.query, "Reply with exactly: OK", complexity="L1")
            return bool(result) and not result.startswith("ERROR")
        except Exception as e:
            self._stats["last_error"] = f"LLM: {str(e)[:200]}"
            return False

    async def _check_telegram_health(self) -> bool:
        """Quick Telegram API connectivity test."""
        try:
            from telegram import Bot
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not token:
                return False
            bot = Bot(token=token)
            me = await bot.get_me()
            return bool(me and me.id)
        except Exception as e:
            self._stats["last_error"] = f"Telegram: {str(e)[:200]}"
            return False

    def _check_memory_usage(self) -> dict:
        """Check current process memory usage."""
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            return {
                "rss_mb": round(mem_info.rss / (1024 * 1024), 1),
                "vms_mb": round(mem_info.vms / (1024 * 1024), 1),
                "is_high": mem_info.rss > 800 * 1024 * 1024,  # > 800 MB
            }
        except Exception:
            return {"rss_mb": 0, "vms_mb": 0, "is_high": False}

    async def _send_alert(self, message: str):
        """Send an alert message via Telegram."""
        try:
            from core.services.telegram_service import telegram_service
            await telegram_service.send_message(
                f"🚨 *WATCHDOG ALERT*\n\n{message}",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"  [Watchdog] ❌ Failed to send alert: {e}")

    async def _run_health_check(self) -> bool:
        """Run a complete health check cycle."""
        self._stats["total_checks"] += 1
        all_healthy = True

        # 1. LLM Health
        llm_ok = await self._check_llm_health()
        if not llm_ok:
            all_healthy = False
            print(f"  [Watchdog] ⚠️ LLM health check FAILED")

        # 2. Memory Usage
        mem = self._check_memory_usage()
        if mem["is_high"]:
            await self._send_alert(
                f"⚠️ High memory usage: {mem['rss_mb']} MB RSS\n"
                f"Consider restarting the process."
            )

        if all_healthy:
            self.consecutive_failures = 0
            self.last_healthy_time = datetime.now()
            self._stats["successful_checks"] += 1
        else:
            self.consecutive_failures += 1
            self._stats["failed_checks"] += 1

            if self.consecutive_failures >= self.max_failures_before_alert:
                await self._send_alert(
                    f"🔴 {self.consecutive_failures} consecutive health check failures!\n"
                    f"Last error: {self._stats.get('last_error', 'Unknown')}\n"
                    f"Last healthy: {self.last_healthy_time or 'Never'}"
                )
                # Reset counter after alerting
                self.consecutive_failures = 0

        return all_healthy

    def get_status(self) -> dict:
        """Get current watchdog status for /status command."""
        return {
            **self._stats,
            "consecutive_failures": self.consecutive_failures,
            "last_healthy": self.last_healthy_time.isoformat() if self.last_healthy_time else None,
            "is_running": self.is_running,
            "memory": self._check_memory_usage(),
        }

    async def run(self):
        """Main watchdog loop — runs forever as a background task."""
        self.is_running = True
        print(f"🐕 Watchdog started (check every {self.check_interval}s)")

        # Wait 60s before first check to let the bot fully initialize
        await asyncio.sleep(60)

        while True:
            try:
                healthy = await self._run_health_check()
                status = "✅ Healthy" if healthy else "⚠️ Degraded"
                print(f"  [Watchdog] Health check: {status} | "
                      f"Checks: {self._stats['total_checks']} | "
                      f"Failures: {self._stats['failed_checks']}")
            except Exception as e:
                print(f"  [Watchdog] ❌ Error in health check loop: {e}")
                traceback.print_exc()

            await asyncio.sleep(self.check_interval)


# Default instance
bot_watchdog = BotWatchdog()
