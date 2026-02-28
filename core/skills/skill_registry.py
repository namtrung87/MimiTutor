import re
from typing import Callable, List, Optional, Dict, Any
from core.utils.bot_logger import get_logger

logger = get_logger("skill_registry")

class Skill:
    def __init__(self, name: str, trigger_patterns: List[str], func: Callable, description: str = ""):
        self.name = name
        self.trigger_patterns = trigger_patterns
        self.func = func
        self.description = description

    def matches(self, text: str) -> bool:
        for pattern in self.trigger_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

class SkillRegistry:
    """
    Registry for deterministic skills that can bypass the full LLM graph.
    """
    def __init__(self):
        self.skills: Dict[str, Skill] = {}

    def register(self, name: str, trigger_patterns: List[str], func: Callable, description: str = ""):
        self.skills[name] = Skill(name, trigger_patterns, func, description)
        logger.info(f"Registered skill: {name}")

    def find_match(self, text: str) -> Optional[Skill]:
        for skill in self.skills.values():
            if skill.matches(text):
                return skill
        return None

    def execute(self, skill_name: str, *args, **kwargs) -> Any:
        if skill_name in self.skills:
            return self.skills[skill_name].func(*args, **kwargs)
        return None

# Global registry instance
skill_registry = SkillRegistry()

# --- Built-in Fast Path Skills ---

def quick_greeting(text: str) -> str:
    return "Chào bạn! Tôi là Orchesta Assistant. Tôi có thể giúp gì cho bạn hôm nay?"

skill_registry.register(
    "greeting",
    [r"^(chào|hi|hello|xin chào)$"],
    quick_greeting,
    "Simple greeting responder"
)

def get_current_time(text: str) -> str:
    from datetime import datetime
    return f"Bây giờ là {datetime.now().strftime('%H:%M, %d/%m/%Y')}."

skill_registry.register(
    "time_check",
    [r"(mấy giờ|thời gian|hôm nay là ngày bao nhiêu)"],
    get_current_time,
    "Get current date and time"
)
