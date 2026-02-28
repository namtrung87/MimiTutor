import functools
import json
from typing import Callable, Any, Optional
from core.utils.bot_logger import get_logger
from core.state import AgentState

logger = get_logger("error_handler")

def with_agent_fallback(fallback_fn: Optional[Callable] = None, max_retries: int = 2):
    """
    Decorator to handle agent execution failures (LLM errors, parsing errors).
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(state: AgentState, *args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(state, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    if attempt < max_retries:
                        # Optional: Add small delay or state modification here
                        continue
            
            logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}. Last error: {last_exception}")
            
            if fallback_fn:
                return fallback_fn(state)
            
            # Default safe fallback
            return {
                "messages": [f"System: [Agent Failure] {func.__name__} failed after retries. Error: {last_exception}"],
                "execution_status": "error"
            }
        return wrapper
    return decorator

def _is_hard_fail(result: Any) -> bool:
    """Helper to detect if a result indicates a hard failure despite no exception."""
    if isinstance(result, dict) and "messages" in result:
        last_msg = result["messages"][-1] if result["messages"] else ""
        return "ERROR:" in str(last_msg) or "HARD_FAIL" in str(last_msg)
    return False
