import os
import random
from dotenv import load_dotenv

load_dotenv()

class OuraClient:
    """
    Client for Oura Ring API.
    For now, uses mock data if no API key is present.
    """
    def __init__(self):
        self.api_key = os.getenv("OURA_API_KEY")
        self.base_url = "https://api.ouraring.com/v2/usercollection/"

    def get_readiness_score(self):
        """Fetch the latest readiness score."""
        if not self.api_key:
            # Mock data for demonstration
            return {
                "score": random.randint(65, 95),
                "contributors": {
                    "hrv_balance": "optimal",
                    "recovery_index": "good",
                    "sleep_balance": "fair"
                },
                "status": "mocked"
            }
        
        # Real implementation would go here (requires requests)
        # return self._fetch_from_api("readiness")
        return {"error": "Real Oura API implementation pending API key verification."}

    def get_sleep_metrics(self):
        """Fetch latest sleep metrics."""
        if not self.api_key:
            return {
                "total_sleep": "7h 45m",
                "rem_sleep": "1h 30m",
                "deep_sleep": "1h 15m",
                "status": "mocked"
            }
        return {"error": "Pending API key."}
