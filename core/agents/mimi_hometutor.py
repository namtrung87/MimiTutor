from core.agents.mimi_router import MimiRouter
from core.agents.socratic_agent import SocraticAgent
from core.state import AgentState
import os

class MimiHomeTutor:
    """
    Combined agent for Mimi's HomeTutor. 
    Handles routing and tutoring logic autonomously, bypassing the Supervisor.
    """
    def __init__(self):
        self.router = MimiRouter()
        self.socratic = SocraticAgent()

    def process_request(self, state: AgentState) -> dict:
        """
        Main entry point for handling Mimi's requests.
        """
        messages = state.get("messages", [])
        user_input = ""
        for msg in reversed(messages):
            if msg and isinstance(msg, str) and not msg.startswith("System:"):
                user_input = msg
                break
        
        if not user_input:
            user_input = messages[-1] if messages else ""
            
        # Clean prefix if any
        user_input_clean = user_input.replace("Mimi: ", "").strip()
        
        # 1. Classify Intent
        print(f"  [MimiHomeTutor] Routing request: {user_input_clean[:50]}...")
        classification = self.router.classify_intent(user_input_clean)
        print(f"  [MimiHomeTutor] Intent: {classification.intent} ({classification.reason})")
        
        # 2. Route to specialized logic
        if classification.intent == "EXERCISE":
            return self.socratic.socratic_node(state)
        elif classification.intent == "THEORY":
            from core.agents.summarize_agent import summarize_agent_node
            return summarize_agent_node(state)
        else:
            from core.agents.scholar_agent import scholar_agent_node
            return scholar_agent_node(state)

def mimi_hometutor_node(state: AgentState):
    agent = MimiHomeTutor()
    return agent.process_request(state)

def build_mimi_graph():
    """
    Simplified graph specifically for Mimi's HomeTutor.
    Bypasses the full Supervisor/Router logic.
    """
    from langgraph.graph import StateGraph, END
    from core.agents.ops_agent import ops_node
    from core.agents.utils_nodes import (
        memory_retrieval_node, 
        finalize_session_node, 
        priority_lookup_node, 
        mimi_logging_node, 
        token_tracker_node
    )
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("ops_guard", ops_node)
    workflow.add_node("memory_retrieval", memory_retrieval_node)
    workflow.add_node("priority_lookup", priority_lookup_node)
    workflow.add_node("mimi_hometutor", mimi_hometutor_node)
    workflow.add_node("mimi_logger", mimi_logging_node)
    workflow.add_node("token_tracker", token_tracker_node)
    workflow.add_node("finalize", finalize_session_node)
    
    workflow.set_entry_point("ops_guard")
    workflow.add_edge("ops_guard", "memory_retrieval")
    workflow.add_edge("memory_retrieval", "priority_lookup")
    workflow.add_edge("priority_lookup", "mimi_hometutor")
    workflow.add_edge("mimi_hometutor", "mimi_logger")
    workflow.add_edge("mimi_logger", "token_tracker")
    workflow.add_edge("token_tracker", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()
