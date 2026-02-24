import json
from core.agents.universal_agent import UniversalAgent
from core.state import AgentState
from skills.wellness.wger_client import WgerClient
from skills.wellness.sparky_client import SparkyClient
from skills.wellness.oura_client import OuraClient

class WellnessAgent(UniversalAgent):
    def __init__(self):
        super().__init__()
        self.wger = WgerClient()
        self.sparky = SparkyClient()
        self.oura = OuraClient()
        self.prompt_map["wellness"] = "wellness_performance_coach"

    def _execute_tool(self, command: str) -> str:
        """Extended tools for wellness."""
        if any(prefix in command for prefix in ["WGER_", "SPARKY_", "OURA_"]):
            parts = command.split(" ", 1)
            action = parts[0].replace("ACTION:", "").upper()
            params = parts[1] if len(parts) > 1 else ""

            if action == "WGER_WORKOUTS":
                return json.dumps(self.wger.get_workout_plans(), indent=2)
            elif action == "WGER_LOG_WEIGHT":
                return json.dumps(self.wger.log_measurement(params), indent=2)
            elif action == "SPARKY_METRICS":
                return json.dumps(self.sparky.get_metrics(), indent=2)
            elif action == "OURA_READINESS":
                return json.dumps(self.oura.get_readiness_score(), indent=2)
            
        return super()._execute_tool(command)

    def process_request(self, state: AgentState) -> dict:
        # Update system prompt with specific wellness tool instructions
        wellness_tools = """
        --- WELLNESS TOOLS ---
        Use these actions if the user asks for data from wger, SparkyFitness, or Oura:
        - ACTION:WGER_WORKOUTS (Fetch workout plans)
        - ACTION:WGER_LOG_WEIGHT 73.0 (Log weight)
        - ACTION:SPARKY_METRICS (Fetch latest body metrics)
        - ACTION:OURA_READINESS (Check recovery/readiness score)
        
        Medicine 3.0 Principles:
        - Zone 2: Steady cardio, conversational pace.
        - Zone 5: VO2 Max sessions.
        - Stability: Foundational movements.
        """
        # Inject additional context into the state for the LLM
        if "wellness_context" not in state:
            state["wellness_context"] = wellness_tools
            
        return super().process_request(state)

def wellness_agent_node(state: AgentState):
    agent = WellnessAgent()
    return agent.process_request(state)
