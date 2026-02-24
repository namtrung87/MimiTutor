import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SparkyClient:
    def __init__(self):
        self.api_url = os.getenv("SPARKY_FITNESS_URL")
        self.api_key = os.getenv("SPARKY_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        } if self.api_key else {}

    def get_metrics(self):
        """Fetch latest health metrics from SparkyFitness."""
        if not self.api_url:
            return {"error": "SparkyFitness URL not configured."}
        url = f"{self.api_url}/api/v1/metrics/latest" # Example endpoint
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                return response.json()
            return {"error": f"Sparky API Error: {response.status_code}"}
        except Exception as e:
            return {"error": f"Connection failed: {e}"}

    def log_activity(self, activity_data):
        """Log a new activity to SparkyFitness."""
        if not self.api_url:
            return {"error": "SparkyFitness URL not configured."}
        url = f"{self.api_url}/api/v1/activities"
        try:
            response = requests.post(url, headers=self.headers, json=activity_data, timeout=5)
            return response.json() if response.status_code in [200, 201] else {"error": response.text}
        except Exception as e:
            return {"error": f"Failed to log activity: {e}"}
