import os
import time
import posthog
from portkey_ai import Portkey
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
        # PostHog Setup
        self.posthog_key = os.getenv("POSTHOG_API_KEY")
        self.posthog_host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
        if self.posthog_key:
            posthog.project_api_key = self.posthog_key
            posthog.host = self.posthog_host
        
        # Portkey Setup for Tracing/Gateway
        self.portkey_key = os.getenv("PORTKEY_API_KEY")
        if self.portkey_key:
            self.portkey = Portkey(api_key=self.portkey_key)
        else:
            self.portkey = None

    def track_event(self, user_id: str, event_name: str, properties: Dict[str, Any]):
        """Tracks an agent event in PostHog."""
        if self.posthog_key:
            print(f"  [PostHog] Tracking event: {event_name} for user: {user_id}")
            posthog.capture(user_id, event_name, properties)
        else:
            print(f"  [PostHog] Warning: API Key missing. Skipping trace for {event_name}")

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
