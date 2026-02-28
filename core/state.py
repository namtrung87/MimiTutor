from typing import Optional, List, Dict, Any, Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict
import operator

def merge_dicts(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    if not left: return right
    if not right: return left
    return {**left, **right}

class AgentState(BaseModel):
    """
    Orchesta Assistant Global State (Pydantic V2).
    Standardizes state management across all agents and crews.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Backward compatibility for TypedDict .get() access."""
        return getattr(self, key, default)

    # Context IDs
    user_id: str = Field(..., description="Unique ID of the user")
    session_id: Optional[str] = Field(None, description="Active session identifier")
    
    # Input/Output
    input_file: Optional[str] = None
    user_input: Optional[str] = None
    file_content: Optional[str] = None
    
    # Processed Data
    extracted_skill: Optional[Dict[str, Any]] = None
    skill_saved: bool = False
    routing_category: Optional[str] = None
    
    # Memory & Automation
    long_term_memory: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    browser_results: Optional[str] = None
    
    # Flow Control
    retry_count: int = 0
    max_retries: int = 3
    is_valid: bool = True
    critic_feedback: Optional[str] = None
    token_tracker: int = 0
    
    # Coding Crew slots
    developer_output: Optional[str] = None
    auditor_output: Optional[str] = None
    research_output: Optional[str] = None
    
    # Reducers: help LangGraph merge parallel outputs
    # Note: Wrap in Annotated for LangGraph compatibility if needed, 
    # but BaseModel already handles most updates.
    messages: Annotated[List[str], operator.add] = Field(default_factory=list)
    
    # Generalized Parallel Perspectives
    parallel_outputs: Annotated[Dict[str, str], merge_dicts] = Field(default_factory=dict)
    
    # Strategy C: Swarm 2.0
    handoff_target: Optional[str] = None
    handoff_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Vibe Coding: Runtime Verification
    verification_logs: Optional[str] = None
    execution_status: Optional[Literal["success", "failure", "pending"]] = "pending"
    
    # Wellness Integration
    readiness_score: Optional[int] = None

    # Output extraction
    final_response: Optional[str] = None
