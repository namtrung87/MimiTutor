from core.utils.llm_manager import LLMManager
from core.state import AgentState
from typing import List, Dict, Any, Optional

llm = LLMManager()

class CriticDebateManager:
    """
    Implements a multi-turn debate between a Primary Responder and a Critic.
    Inspired by AutoGen's ConversableAgent pattern.
    """
    
    def __init__(self, rounds: int = 2):
        self.max_rounds = rounds

    def run_debate(self, user_input: str, initial_response: str) -> str:
        """
        Runs a debate loop to refine the initial response.
        """
        current_response = initial_response
        debate_history = []
        
        print(f"  [Debate] Starting {self.max_rounds}-round critique...")
        
        for i in range(self.max_rounds):
            # 1. Critic Round
            critic_prompt = f"""
            You are a STERN CRITIC. 
            USER REQUEST: {user_input}
            CURRENT RESPONSE: {current_response}
            
            Identify 3 logical flaws, missed requirements, or pedagogical improvements.
            Be concise and blunt.
            """
            critique = llm.query(critic_prompt, complexity="L2", domain="reasoning")
            print(f"    [Round {i+1}] Critic: {critique[:50]}...")
            
            # 2. Rebuttal/Fix Round
            fix_prompt = f"""
            You are a HELPFUL AGENT.
            USER REQUEST: {user_input}
            ORIGINAL RESPONSE: {current_response}
            CRITIQUE RECEIVED: {critique}
            
            Address the critique and provide a revised, better response.
            Maintain the original goal but fix the flaws.
            """
            current_response = llm.query(fix_prompt, complexity="L3", domain="reasoning")
            print(f"    [Round {i+1}] Responder: Refined version ready.")
            
            debate_history.append({"round": i+1, "critique": critique, "revision": current_response})
            
        return current_response

def debate_node(state: AgentState):
    """
    LangGraph node for high-precision debate.
    """
    user_input = state.messages[-1]
    # We assume 'developer_output' or the last message is what we debate
    initial_text = state.developer_output or state.messages[-1]
    
    manager = CriticDebateManager(rounds=1) # 1 round for efficiency
    refined_text = manager.run_debate(user_input, initial_text)
    
    return {
        "messages": [f"System: Final Debated Response: {refined_text}"],
        "critic_feedback": "Debate complete."
    }
