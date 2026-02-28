import os
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class ObservabilityManager:
    """
    Handles Agentic Observability:
    1. Tracing via Portkey (AI Gateway)
    2. Analytics via PostHog (Event Tracking)
    3. Performance Monitoring (Latency/Tokens)
    """
    def __init__(self):
        self.posthog_key = os.getenv("POSTHOG_API_KEY")
        self.posthog_host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
        self.portkey_key = os.getenv("PORTKEY_API_KEY")
        self._posthog_client = None
        self._portkey_client = None

    @property
    def posthog(self):
        """Lazy-load posthog."""
        if self._posthog_client is None and self.posthog_key:
            try:
                import posthog
                posthog.project_api_key = self.posthog_key
                posthog.host = self.posthog_host
                self._posthog_client = posthog
            except ImportError:
                print("  [Observability] Posthog not installed.")
        return self._posthog_client

    @property
    def portkey(self):
        """Lazy-load portkey."""
        if self._portkey_client is None and self.portkey_key:
            try:
                from portkey_ai import Portkey
                self._portkey_client = Portkey(api_key=self.portkey_key)
            except ImportError:
                print("  [Observability] Portkey not installed.")
        return self._portkey_client

    def track_event(self, user_id: str, event_name: str, properties: Dict[str, Any]):
        """Tracks an agent event in PostHog."""
        client = self.posthog
        if client:
            print(f"  [PostHog] Tracking event: {event_name} for user: {user_id}")
            client.capture(user_id, event_name, properties)
        else:
            # Only print if key exists but client failed, otherwise stay silent
            if self.posthog_key:
                print(f"  [PostHog] Warning: Failed to initialize. Skipping trace for {event_name}")

    def start_trace(self, trace_id: str, component: str):
        """Mock/Utility for starting a trace span (useful for Portkey/LangSmith)."""
        return {
            "trace_id": trace_id,
            "component": component,
            "start_time": time.time()
        }

    def end_trace(self, trace_ctx: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Ends a trace and calculates duration."""
        duration = time.time() - trace_ctx["start_time"]
        user_id = metadata.get("user_id", "anonymous") if metadata else "anonymous"
        
        props = {
            "component": trace_ctx["component"],
            "duration_seconds": duration,
            **(metadata or {})
        }
        self.track_event(user_id, f"agent_execution_finished", props)
        return duration

# Global instance
obs = ObservabilityManager()
