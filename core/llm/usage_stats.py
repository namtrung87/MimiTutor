import json
from pathlib import Path
from datetime import datetime
from core.utils.bot_logger import get_logger

logger = get_logger("usage_stats")

class UsageStats:
    """
    Tracks token usage and estimated costs for different LLM providers via LiteLLM.
    """
    STATS_FILE = Path("usage_stats.json")
    DAILY_BUDGET_VND = 50000.0 # ~ $2.00 per day limit for automated tasks
    EXCHANGE_RATE = 25000.0 # USD to VND conversion rate

    @classmethod
    def set_daily_budget(cls, amount: float):
        cls.DAILY_BUDGET_VND = amount

    @classmethod
    def log_usage(cls, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        try:
            stats = {}
            if cls.STATS_FILE.exists():
                with open(cls.STATS_FILE, "r") as f:
                    stats = json.load(f)
            
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in stats:
                stats[today] = {"total_cost_vnd": 0, "models": {}}
            
            # Use LiteLLM cost if possible, or estimated fallback
            try:
                import litellm
                cost_usd = litellm.completion_cost(model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens) or 0
                cost_vnd = cost_usd * cls.EXCHANGE_RATE
            except:
                # Fallback: differentiate between 'pro' and 'flash' models
                is_pro = "pro" in model.lower() or "large" in model.lower() or "4o" in model.lower()
                rate = 0.5 if is_pro else 0.05
                cost_vnd = (prompt_tokens + completion_tokens) * rate
            
            if model not in stats[today]["models"]:
                stats[today]["models"][model] = {"prompt": 0, "completion": 0, "cost_vnd": 0}
            
            stats[today]["models"][model]["prompt"] += prompt_tokens
            stats[today]["models"][model]["completion"] += completion_tokens
            stats[today]["models"][model]["cost_vnd"] += cost_vnd
            stats[today]["total_cost_vnd"] += cost_vnd
            
            with open(cls.STATS_FILE, "w") as f:
                json.dump(stats, f, indent=2)
            
            if stats[today]["total_cost_vnd"] > cls.DAILY_BUDGET_VND:
                logger.warning(f"⚠️ DAILY BUDGET EXCEEDED: {stats[today]['total_cost_vnd']:.1f} VND / {cls.DAILY_BUDGET_VND} VND")
                
        except Exception as e:
            logger.error(f"Error logging usage: {e}")

    @classmethod
    def record_usage(cls, model: str, p_tokens: int, c_tokens: int):
        """Simple manual log for testing."""
        cls.log_usage(model, p_tokens, c_tokens)

    @classmethod
    def get_todays_cost(cls) -> float:
        try:
            if not cls.STATS_FILE.exists(): return 0.0
            with open(cls.STATS_FILE, "r") as f:
                stats = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            return stats.get(today, {}).get("total_cost_vnd", 0.0)
        except:
            return 0.0

    @classmethod
    def is_within_budget(cls) -> bool:
        """Returns True if the current daily spend is below the limit."""
        return cls.get_todays_cost() < cls.DAILY_BUDGET_VND

    @classmethod
    def get_budget_status(cls) -> str:
        cost = cls.get_todays_cost()
        percent = (cost / cls.DAILY_BUDGET_VND) * 100
        return f"Daily Spend: {cost:.1f}/{cls.DAILY_BUDGET_VND} VND ({percent:.1f}%)"
