class TokenMonitor:
    """Middleware to monitor token usage in real-time."""
    QUOTAS = {"L1": 1000, "L2": 5000, "L3": 20000}
    @classmethod
    def check_and_interrupt(cls, complexity: str, current_usage: int) -> bool:
        quota = cls.QUOTAS.get(complexity, 5000)
        return current_usage > quota
