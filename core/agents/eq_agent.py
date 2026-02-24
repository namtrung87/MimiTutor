from core.state import AgentState
from typing import Dict, Any

class EQAgent:
    """
    Agent responsible for Emotional Intelligence and Nervous System Regulation.
    Analyzes physiological data to predict emotional load and suggest interventions.
    """
    def __init__(self):
        pass

    def analyze_emotional_load(self, state: AgentState) -> Dict[str, Any]:
        """
        Predict mood/stress levels based on HRV and REM sleep.
        """
        readiness = state.get("readiness_score", 70)
        # Mocking REM/HRV data extraction from state or external source
        # In a real scenario, this would come from OuraClient.get_sleep_metrics()
        
        load_score = 100 - readiness
        mood = "Stable"
        intervention = None

        if load_score > 40:
            mood = "High Emotional Load / Stressed"
            intervention = "Physiological Sigh: Inhale deeply through nose, follow with a second short inhale, then long exhale through mouth."
        elif load_score > 25:
            mood = "Moderate Tension"
            intervention = "Box Breathing: 4s inhale, 4s hold, 4s exhale, 4s hold."
        
        return {
            "mood": mood,
            "emotional_load_score": load_score,
            "suggested_intervention": intervention
        }

    def process_request(self, state: AgentState) -> Dict[str, Any]:
        analysis = self.analyze_emotional_load(state)
        
        msg = f"System: EQ Agent Analysis: Trạng thái hiện tại: {analysis['mood']}."
        if analysis['suggested_intervention']:
            msg += f"\n👉 Khuyên nghị: {analysis['suggested_intervention']}"
            
        return {
            "messages": [msg],
            "emotional_state": analysis
        }

def eq_agent_node(state: AgentState):
    agent = EQAgent()
    return agent.process_request(state)
