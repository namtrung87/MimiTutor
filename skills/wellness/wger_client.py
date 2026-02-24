import os
import requests
from dotenv import load_dotenv

load_dotenv()

class WgerClient:
    def __init__(self):
        self.api_key = os.getenv("WGER_API_KEY")
        self.base_url = "https://wger.de/api/v2/"
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Accept": "application/json"
        } if self.api_key else {"Accept": "application/json"}

    def list_exercises(self, language=2): # 2 is English, 1 is German
        """List exercises from wger."""
        url = f"{self.base_url}exercise/?language={language}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Failed to fetch exercises: {response.status_code}"}

    def get_workout_plans(self):
        """Get user's workout plans (requires authentication)."""
        if not self.api_key:
            return {"error": "API Key required for workout plans."}
        url = f"{self.base_url}workout/"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Failed to fetch workouts: {response.status_code}"}

    def log_measurement(self, weight, date=None):
        """Log body weight measurement."""
        if not self.api_key:
            return {"error": "API Key required to log measurements."}
        url = f"{self.base_url}weightentry/"
        data = {
            "date": date or requests.utils.quote(os.popen("date /t").read().strip()), # Simple date fallback
            "weight": weight
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code in [200, 201]:
            return response.json()
        return {"error": f"Failed to log weight: {response.status_code}"}
