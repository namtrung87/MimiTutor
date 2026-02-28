import os
from pathlib import Path
from core.utils.bot_logger import get_logger

logger = get_logger("prompt_loader")

class PromptLoader:
    """
    Utility to load system prompts from the prompts/ directory.
    Uses lazy loading and caching.
    """
    _cache = {}
    PROMPTS_DIR = Path("prompts")

    @classmethod
    def load(cls, prompt_name: str) -> str:
        """
        Loads a prompt by name (filename without .md extension).
        """
        if prompt_name in cls._cache:
            return cls._cache[prompt_name]
        
        file_path = cls.PROMPTS_DIR / f"{prompt_name}.md"
        
        if not file_path.exists():
            logger.warning(f"Prompt file not found: {file_path}. Using fallback.")
            return f"You are a helpful AI assistant named {prompt_name}."

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                cls._cache[prompt_name] = content
                return content
        except Exception as e:
            logger.error(f"Error loading prompt {prompt_name}: {e}")
            return f"Error loading prompt: {e}"

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()
