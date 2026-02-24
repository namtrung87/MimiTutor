from core.state import AgentState
from core.utils.llm_manager import LLMManager
from core.agents.universal_agent import UniversalAgent
import json
import asyncio

llm = LLMManager()

def developer_node(state: AgentState):
    """Focuses on implementing the requested feature/fix."""
    user_input = state["messages"][-1]
    memory = state.get("long_term_memory", [])
    v_logs = state.get("verification_logs")
    v_status = state.get("execution_status")
    
    error_context = ""
    if v_status == "failure" and v_logs:
        error_context = f"\n\nCRITICAL: The previous implementation FAILED verification with the following logs:\n{v_logs}\nPlease fix these errors in your new implementation."

    prompt = f"""
    You are a Senior Software Developer. 
    Mission: Implement the following request with clean, efficient code.
    
    USER REQUEST: {user_input}
    CONTEXT/MEMORY: {memory}{error_context}
    
    Return your implementation and a brief technical explanation.
    """
    print("  [CodingCrew] Developer working with High Thinking Depth...")
    # Leveraging L3 for development to ensure Opus-level quality
    response = llm.query(prompt, complexity="L2", domain="tech")
    return {"developer_output": response}

def auditor_node(state: AgentState):
    """Focuses on security, edge cases, and logical consistency."""
    user_input = state["messages"][-1]
    
    prompt = f"""
    You are a Senior Security Auditor and QA Engineer.
    Mission: Identify potential security vulnerabilities, edge cases, and logical flaws in the following request.
    
    USER REQUEST: {user_input}
    
    Do NOT write code yet. Provide a list of critical constraints and risks that MUST be addressed.
    """
    print("  [CodingCrew] Auditor analyzing risks with Comprehensive Depth...")
    # Use L3 for audit to identify subtle edge cases
    response = llm.query(prompt, complexity="L2", domain="tech")
    return {"auditor_output": response}

def researcher_node(state: AgentState):
    """Uses LLMManager directly for fast tech research (no MCP overhead)."""
    user_input = state["messages"][-1] if state.get("messages") else ""
    
    print("  [CodingCrew] Researcher gathering documentation...")
    prompt = f"""You are a Senior Technical Researcher.
    Find best practices, patterns, and documentation references for implementing:
    {user_input}
    
    Provide concise, actionable technical guidance."""
    
    response = llm.query(prompt, complexity="L2", domain="tech")
    return {"research_output": response or "No research found."}

def synthesis_node(state: AgentState):
    """Merges all outputs into a final high-quality answer."""
    dev = state.get("developer_output", "No implementation provided.")
    audit = state.get("auditor_output", "No audit provided.")
    res = state.get("research_output", "No research provided.")
    user_input = state["messages"][-1]
    
    prompt = f"""
    You are the Lead Architect. Match the Developer's code against the Auditor's risks and the Researcher's documentation.
    
    USER ORIGINAL REQUEST: {user_input}
    
    DEVELOPER PROPOSAL:
    {dev}
    
    AUDITOR'S CRITIQUE/RISKS:
    {audit}
    
    DOCUMENTATION/RESEARCH:
    {res}
    
    MISSION:
    1. Reconcile the perspectives.
    2. Correct the Developer's code if it violates Auditor's safety rules or Researcher's docs.
    3. Present the FINAL, optimized solution to the user.
    """
    print("  [CodingCrew] Lead Architect synthesizing final solution (128K Output Ready)...")
    # Lead Architect uses L3 for maximum reasoning and output capacity
    final_response = llm.query(prompt, complexity="L2", domain="tech")
    
    return {"messages": [f"Coding Crew: {final_response}"]}
