import json
import os
from datetime import datetime
from core.agents.universal_agent import UniversalAgent
from core.state import AgentState

class CommuteLogicAgent(UniversalAgent):
    def __init__(self):
        super().__init__()
        self.prompt_map["commute"] = "commute_meta_alchemist"
        self.commute_data_path = os.path.join(os.path.dirname(__file__), "../../commute_state.json")
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.commute_data_path):
            with open(self.commute_data_path, "r") as f:
                self.state_data = json.load(f)
        else:
            self.state_data = {
                "active_mode": "idle",
                "total_insights": 0,
                "game_rewards_pending": 0,
                "recovery_points": 0,
                "last_sync": datetime.now().isoformat()
            }

    def _save_state(self):
        self.state_data["last_sync"] = datetime.now().isoformat()
        with open(self.commute_data_path, "w") as f:
            json.dump(self.state_data, f, indent=2)

    def process_request(self, state: AgentState) -> dict:
        user_input = state["messages"][-1]
        
        # Internal Logic Bridge
        if "SET_MODE:" in user_input:
            mode = user_input.split("SET_MODE:")[1].strip()
            self.state_data["active_mode"] = mode
            self._save_state()
            state["messages"].append(f"System: Commute Mode set to {mode}")
            return {"messages": state["messages"]}

        # Phase 3: Voice-to-Insight (Commute Mode 2.0)
        if "VOICE_TRANSCRIBED:" in user_input:
            raw_transcript = user_input.split("VOICE_TRANSCRIBED:")[1].strip()
            print(f"  [CommuteAgent] Refining noisy transcript: {raw_transcript[:50]}...")
            
            prompt = f"""
            You are the Commute Alchemist. 
            The following text is a transcript from a voice note recorded in a noisy shuttle bus.
            Refine the text, remove noise, and extract 'Mindset Changers' or 'Actionable Insights'.
            
            TRANSCRIPT:
            {raw_transcript}
            
            Format as a clear, bulleted list of 1-3 insights.
            """
            refined = self.llm.query(prompt, complexity="L2")
            self.state_data["total_insights"] += 1
            self._save_state()
            return {"messages": [f"🚌 [Commute Mode] Insight đã được tinh lọc:\n{refined}"]}

        if "ADD_INSIGHT" in user_input:
            self.state_data["total_insights"] += 1
            self._save_state()
            state["messages"].append(f"System: Insight recorded. Total: {self.state_data['total_insights']}")
            return {"messages": state["messages"]}

        # Default to LLM processing for complex commute strategy questions
        return super().process_request(state)

def commute_agent_node(state: AgentState):
    agent = CommuteLogicAgent()
    return agent.process_request(state)
