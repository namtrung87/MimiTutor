from core.agents.mimi_router import MimiRouter
from core.agents.socratic_agent import SocraticAgent
from core.state import AgentState
import os
import traceback

# Module-level static fallback
_MIMI_AGENT_FALLBACK = "Chị hiểu câu hỏi của em rồi! Nhưng chị cần thêm một chút thời gian để suy nghĩ..."

# Module-level lazy singletons
_router_instance = None
_socratic_instance = None

class MimiHomeTutor:
    """
    Combined agent for Mimi's HomeTutor. 
    Handles routing and tutoring logic autonomously, bypassing the Supervisor.
    """
    def __init__(self):
        global _router_instance, _socratic_instance
        if _router_instance is None:
            _router_instance = MimiRouter()
        if _socratic_instance is None:
            _socratic_instance = SocraticAgent()
        self.router = _router_instance
        self.socratic = _socratic_instance

    def process_request(self, state: AgentState) -> dict:
        """
        Main entry point for handling Mimi's requests with progressive fallback.
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
        
        # Step 1: Classify (with its own error handling)
        try:
            print(f"  [MimiHomeTutor] Routing request: {user_input_clean[:50]}...")
            classification = self.router.classify_intent(user_input_clean)
            print(f"  [MimiHomeTutor] Intent: {classification.intent} ({classification.reason})")
        except Exception as e:
            print(f"  [MimiHomeTutor] Router failed: {e}. Defaulting to EXERCISE.")
            from core.agents.mimi_router import IntentClassification
            classification = IntentClassification(intent="EXERCISE", reason="Router exception fallback")

        # Step 2: Execute agent (with progressive fallback)
        try:
            if classification.intent == "EXERCISE":
                return self.socratic.socratic_node(state)
            elif classification.intent == "THEORY":
                from core.agents.summarize_agent import summarize_agent_node
                return summarize_agent_node(state)
            else:
                from core.agents.scholar_agent import scholar_agent_node
                return scholar_agent_node(state)
        except Exception as e:
            print(f"  [MimiHomeTutor] Agent execution failed: {e}", flush=True)
            traceback.print_exc()

        # Step 3: Progressive fallback - try rule-based response
        try:
            fallback = self.socratic._get_rule_based_socratic_response(user_input_clean, "")
            return {
                "messages": [f"Mimi Agent: {fallback}"],
                "final_response": fallback
            }
        except Exception as e:
            print(f"  [MimiHomeTutor] Even rule-based fallback failed: {e}")
            return {
                "messages": [f"Mimi Agent: {_MIMI_AGENT_FALLBACK}"],
                "final_response": _MIMI_AGENT_FALLBACK
            }

def mimi_hometutor_node(state: AgentState):
    global _mimi_instance
    if '_mimi_instance' not in globals() or _mimi_instance is None:
        _mimi_instance = MimiHomeTutor()
    return _mimi_instance.process_request(state)

def hometutor_routing(state: AgentState):
    final_response = state.get("final_response", "")
    if not isinstance(final_response, str):
        final_response = ""
    if not isinstance(final_response, str):
        final_response = ""
    
    # Hard fallback markers that indicate infrastructure failure (no point retrying)
    HARD_FAIL_MARKERS = ["cần thêm một chút thời gian", "đứt dòng"]
    is_hard_fail = any(m in final_response for m in HARD_FAIL_MARKERS)

    if is_hard_fail:
        # Don't retry infrastructure failures - go straight to logger
        return "mimi_logger"

    # All other responses go through critic for quality check
    return "critic"

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
    from core.agents.critic_agent import critic_node
    workflow.add_node("critic", critic_node)
    workflow.add_node("mimi_logger", mimi_logging_node)
    
    # ... (skipping some nodes)
    
    # Dynamic Routing after agent execution
    workflow.add_conditional_edges(
        "mimi_hometutor",
        hometutor_routing,
        {
            "mimi_logger": "mimi_logger",
            "critic": "critic"
        }
    )
    
    workflow.add_conditional_edges(
        "critic",
        lambda x: "mimi_logger" if x.get("routing_category") == "critique_approve" else "mimi_hometutor",
        {
            "mimi_logger": "mimi_logger",
            "mimi_hometutor": "mimi_hometutor"
        }
    )
    
    workflow.add_edge("mimi_logger", "token_tracker")
    workflow.add_edge("token_tracker", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()
