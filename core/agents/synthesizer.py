from core.state import AgentState
from core.utils.llm_manager import LLMManager

llm = LLMManager()

def synthesis_node(state: AgentState):
    """
    Final synthesis node that collects all parallel outputs and produces a unified response.
    """
    parallel_outputs = state.get("parallel_outputs", {})
    user_input = state["messages"][-1]
    
    if not parallel_outputs:
        # Fallback if no parallel work was done
        return {"messages": ["System: Synthesis skipped - no parallel data found."]}

    # Construct the synthesis prompt
    perspectives_str = ""
    for role, content in parallel_outputs.items():
        perspectives_str += f"\n--- {role.upper()} PERSPECTIVE ---\n{content}\n"

    prompt = f"""
    You are the Chief Coordinator & Lead Strategist. 
    Mission: Synthesize multiple specialized perspectives into a final, high-quality, and actionable response for the user.
    
    USER ORIGINAL REQUEST: {user_input}
    
    {perspectives_str}
    
    GUIDELINES:
    1. Acknowledge the different perspectives gathered.
    2. Reconcile any conflicting views.
    3. Synthesize the takeaways into a cohesive "Final Answer".
    4. Provide clear next steps or "chốt lại" (final conclusion).
    
    Return your final response in the same language as the user's request (Vietnamese if the request is in Vietnamese).
    """
    
    print("  [Synthesizer] Merging all perspectives...")
    final_response = llm.query(prompt, complexity="L3", domain="advisor")
    
    return {"messages": [f"Parallel Crew Synthesis: {final_response}"]}
