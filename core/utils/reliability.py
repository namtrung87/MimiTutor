import time
import random
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable
from core.utils.bot_logger import get_logger

logger = get_logger("reliability")

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self, 
        name: str, 
        failure_threshold: int = 3, 
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.last_success_time: float = 0.0

    def record_success(self):
        if self.state != CircuitState.CLOSED:
            logger.info(f"Circuit Breaker '{self.name}' recovered to CLOSED state.")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_success_time = time.time()

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(f"Circuit Breaker '{self.name}' OPENED due to {self.failure_count} failures.")
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info(f"Circuit Breaker '{self.name}' switched to HALF-OPEN state.")
                self.state = CircuitState.HALF_OPEN
                return True
            return False
            
        if self.state == CircuitState.HALF_OPEN:
            return True
            
        return False

    async def execute(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        if not self.can_execute():
            raise RuntimeError(f"Circuit Breaker '{self.name}' is OPEN. Execution blocked.")
            
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exceptions as e:
            self.record_failure()
            raise e

    def execute_sync(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        if not self.can_execute():
            raise RuntimeError(f"Circuit Breaker '{self.name}' is OPEN. Execution blocked.")
            
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exceptions as e:
            self.record_failure()
            raise e

def get_exponential_backoff_with_jitter(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculates exponential backoff with decorrelated jitter."""
    delay = min(max_delay, base_delay * (2 ** attempt))
    jitter = delay * 0.1
    return delay + random.uniform(-jitter, jitter)

class ProviderHealthRegistry:
    """Tracks health state across multiple LLM providers."""
    _breakers: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_breaker(cls, provider_name: str) -> CircuitBreaker:
        if provider_name not in cls._breakers:
            cls._breakers[provider_name] = CircuitBreaker(provider_name)
        return cls._breakers[provider_name]

    @classmethod
    def is_provider_healthy(cls, provider_name: str) -> bool:
        return cls.get_breaker(provider_name).can_execute()
