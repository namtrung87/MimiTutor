import json
import os
import datetime
from typing import Dict, Any, List

class MimiLearningTracker:
    """
    Tracks Mimi's progress across educational subjects.
    Maintains a profile of strengths, weaknesses, and completed topics.
    """
    def __init__(self, user_id: str = "mimi"):
        self.user_id = user_id
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.profile_path = os.path.join(base_dir, "data", f"mimi_learning_profile.json")
        self.profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_updated": datetime.date.today().isoformat(),
            "subjects": {
                "Math": {"level": 7, "progress": 0, "strengths": [], "weaknesses": []},
                "Science": {"level": 7, "progress": 0, "strengths": [], "weaknesses": []},
                "English": {"level": 7, "progress": 0, "strengths": [], "weaknesses": []},
                "Literature": {"level": 7, "progress": 0, "strengths": [], "weaknesses": []}
            },
            "recent_sessions": []
        }

    def _save_profile(self):
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        self.profile["last_updated"] = datetime.date.today().isoformat()
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, indent=2, ensure_ascii=False)

    def log_session(self, subject: str, topic: str, performance: str, mastery_delta: int):
        """Logs a learning session and updates subject progress."""
        if subject not in self.profile["subjects"]:
            self.profile["subjects"][subject] = {"level": 7, "progress": 0, "strengths": [], "weaknesses": []}
        
        sub = self.profile["subjects"][subject]
        sub["progress"] = max(0, min(100, sub["progress"] + mastery_delta))
        
        session = {
            "date": datetime.date.today().isoformat(),
            "subject": subject,
            "topic": topic,
            "performance": performance,
            "mastery_delta": mastery_delta
        }
        self.profile["recent_sessions"].append(session)
        if len(self.profile["recent_sessions"]) > 20:
            self.profile["recent_sessions"].pop(0)
            
        self._save_profile()

    def get_summary(self) -> str:
        """Returns a string summary of Mimi's current progress."""
        lines = [f"📊 **Mimi's Learning Profile (Updated: {self.profile['last_updated']})**"]
        for sub_name, data in self.profile["subjects"].items():
            lines.append(f"- **{sub_name}**: Lớp {data['level']} | Tiến độ: {data['progress']}%")
        return "\n".join(lines)

learning_tracker = MimiLearningTracker()
