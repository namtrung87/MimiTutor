from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PlanningStep(BaseModel):
    step_number: int
    agent: str = Field(description="The agent node to invoke (e.g., developer, researcher_p)")
    task: str = Field(description="The specific instruction for this agent")
    expected_output: str = Field(description="What the agent should produce")

class ExecutionPlan(BaseModel):
    steps: List[PlanningStep]
    rationale: str

class ReflectionLog(BaseModel):
    success: bool
    lessons_learned: List[str]
    suggested_memory: Optional[str] = Field(description="A fact or preference to store in Semantic Memory")

class MessageHistory(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
