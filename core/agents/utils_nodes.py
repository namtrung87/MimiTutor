import os
import time
from core.state import AgentState
from core.utils.observability import obs
from core.utils.memory_manager import memory_manager
from core.utils.llm_manager import ContextPruner
from core.utils.priority_memory import priority_memory
from core.utils.interaction_logger import logger as interaction_logger
from skills.wellness.oura_client import OuraClient

def memory_retrieval_node(state: AgentState):
    """Phase 3: Fetches long-term memory."""
    user_id = state.get("user_id", "default_user")
    user_input = state["messages"][-1] if state.get("messages") else ""
    
    # Start Trace for Memory
    trace_ctx = obs.start_trace(f"memory_{user_id}", "memory_retrieval")
    
    if user_input:
        memories = memory_manager.search_memories(str(user_input), user_id=user_id)
        simplified = [m["text"] for m in memories] if memories else []
        
        # Opus 4.6 Optimization: Compact context if it's getting heavy
        if len(simplified) > 5:
            print("  [Supervisor] Applying Context Compaction to memories...")
            simplified = ContextPruner.compact_context(simplified)
            
        obs.end_trace(trace_ctx, {"found": len(simplified)})
        return {"long_term_memory": simplified, "messages": [f"System: Retrieved {len(simplified)} memories (Compacted)."]}
    
    obs.end_trace(trace_ctx, {"found": 0})
    return {"messages": ["System: No input for memory retrieval."]}

def retry_increment_node(state: AgentState):
    """Increments the retry counter and clears technical routing to allow re-evaluation."""
    count = state.get("retry_count", 0) + 1
    print(f"  [System] Incrementing retry count to {count}")
    return {"retry_count": count, "routing_category": None}

def finalize_session_node(state: AgentState):
    """Phase 3: Saves memory. Phase 4: Monitoring."""
    user_id = state.get("user_id", "default_user")
    messages = state.get("messages", [])
    
    # Phase 4 Monitoring
    obs.track_event(user_id, "session_completed", {
        "message_count": len(messages),
        "category": state.get("routing_category")
    })
    
    if len(messages) >= 2:
        user_msg = messages[-2]
        ai_msg = messages[-1]
        memory_manager.add_memory(
            f"User: {user_msg}\nAssistant: {ai_msg}", 
            user_id=user_id
        )
        return {"messages": ["System: Session finalized & memories stored."]}
    return {"messages": ["System: Skip memory update."]}

def priority_lookup_node(state: AgentState):
    """Checks for golden answers in priority memory before LLM query."""
    messages = state.get("messages", [])
    if not messages: return {}
    
    user_input = ""
    for msg in reversed(messages):
        if msg and isinstance(msg, str) and not msg.startswith("System:"):
            user_input = msg
            break
    
    if user_input:
        user_input_clean = user_input.replace("Mimi: ", "").strip()
        priority_answer = priority_memory.find_priority_answer(user_input_clean)
        if priority_answer:
            return {
                "messages": [f"Mimi Agent: {priority_answer}"],
                "routing_category": "priority_hit" # Signal to skip agents
            }
    return {}

def mimi_logging_node(state: AgentState):
    """Logs the interaction to SQLite for parent review."""
    messages = state.get("messages", [])
    if len(messages) < 2: return {}
    
    user_input = ""
    for msg in messages:
        if isinstance(msg, str) and msg.startswith("Mimi:"):
            user_input = msg.replace("Mimi: ", "").strip()
            break
            
    # Find last agent response
    agent_output = ""
    for msg in reversed(messages):
        if isinstance(msg, str) and any(prefix in msg for prefix in ["Mimi Agent:", "Summarize Agent:", "Socratic Agent:"]):
            agent_output = msg
            break
            
    if user_input and agent_output:
        tags = ["#Study", "#Mimi"]
        if "exercise" in str(state.get("routing_category", "")): tags.append("#Exercise")
        
        interaction_logger.log_interaction(
            user_id=state.get("user_id", "default_user"),
            user_input=user_input,
            intent=state.get("routing_category", "unknown"),
            agent_thought="Refined routing through bifurcated agents.",
            agent_output=agent_output,
            tags=tags,
            metadata={"source": "mimi_tutor"}
        )
    return {}

def token_tracker_node(state: AgentState):
    """Tracks cumulative token usage."""
    messages = state.get("messages", [])
    # Rough estimate: 4 chars = 1 token
    total_chars = sum(len(str(m)) for m in messages)
    total_tokens = total_chars // 4
    
    current_tracker = state.get("token_tracker", 0)
    new_tracker = current_tracker + total_tokens
    
    print(f"  [System] Token Tracker: {new_tracker} (Added {total_tokens})")
    return {"token_tracker": new_tracker, "messages": [f"System: Token Tracker: {new_tracker} (Added {total_tokens})"]}

def readiness_check_node(state: AgentState):
    """Fetches user readiness to adapt system behavior."""
    try:
        oura = OuraClient()
        score_data = oura.get_readiness_score()
        score = score_data.get("score", 70)
    except:
        score = 70
    print(f"  [System] Readiness Check: {score}")
    return {"readiness_score": score, "messages": [f"System: Biometric Readiness is {score}%"]}
