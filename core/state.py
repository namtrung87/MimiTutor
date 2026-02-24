from typing import TypedDict, Optional, List, Dict, Any, Annotated, Literal

def merge_dicts(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    if not left: return right
    if not right: return left
    return {**left, **right}
import operator

class AgentState(TypedDict):
    # Context IDs
    user_id: str
    session_id: Optional[str]
    
    # Input/Output
    input_file: Optional[str]
    user_input: Optional[str]
    file_content: Optional[str]
    
    # Processed Data
    extracted_skill: Optional[Dict[str, Any]]
    skill_saved: bool
    routing_category: Optional[str]
    
    # Phase 3: Memory & Automation
    long_term_memory: Optional[List[Dict[str, Any]]]
    browser_results: Optional[str]
    
    # Flow Control
    retry_count: int
    max_retries: int
    is_valid: bool
    critic_feedback: Optional[str] # Phase 5: Feedback for revision
    token_tracker: Optional[int]  # Phase 6: Cumulative token usage
    
    # Parallel Coding Crew slots (Old/Specific)
    developer_output: Optional[str]
    auditor_output: Optional[str]
    research_output: Optional[str]
    
    # Reducers: help LangGraph merge parallel outputs
    messages: Annotated[List[str], operator.add]
    
    # Phase 6: Generalized Parallel Perspectives
    parallel_outputs: Annotated[Dict[str, str], merge_dicts]
    
    # Strategy C: Swarm 2.0
    handoff_target: Optional[str] # The name of the agent to hand off to
    handoff_metadata: Optional[Dict[str, Any]] # Context for the handoff

    # Vibe Coding: Runtime Verification
    verification_logs: Optional[str] # Captured stdout/stderr from execution
    execution_status: Optional[Literal["success", "failure", "pending"]] # Status of code execution
    
    # Personal Development: Wellness Integration
    readiness_score: Optional[int] # Oura Ring Readiness Score (0-100)
