import random

class PerformanceProtocols:
    """
    Skill for Huberman Lab & Medicine 3.0 protocols.
    """
    def __init__(self):
        self.protocols = {
            "morning": {
                "name": "Morning Foundation",
                "steps": [
                    "Sunlight exposure: 10-15m (within 30m of waking)",
                    "Hydration: 500ml water + electrolytes",
                    "Delay caffeine: Wait 90-120 minutes",
                    "Movement: 10m Zone 2 or Yoga"
                ]
            },
            "recovery": {
                "nsdr": "Link: https://www.youtube.com/watch?v=AKGrmY8OSHM (10-minute NSDR)",
                "yoga_nidra": "Link: https://www.youtube.com/watch?v=pLhJpE99_T0 (20-minute Yoga Nidra)"
            },
            "contrast_therapy": {
                "standard": "Sauna: 15m (180°F) -> Cold Plunge: 3m (50°F) x 3 rounds",
                "night_recovery": "Hot bath (40°C): 20m -> Cold rinse: 1m"
            }
        }

    def get_morning_checklist(self):
        return self.protocols["morning"]

    def get_recovery_advice(self, current_vibe="tired"):
        if current_vibe == "tired":
            return self.protocols["recovery"]["nsdr"]
        return "Keep focusing on Deep Work until your next break."

    def get_protocol(self, category):
        return self.protocols.get(category, {"error": "Protocol not found"})
