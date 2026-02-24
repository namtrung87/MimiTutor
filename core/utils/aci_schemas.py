from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any

class PriorityMemorySchema(BaseModel):
    """Schema for adding/finding golden answers."""
    question: str = Field(..., description="The user's question or intent.")
    answer: str = Field(..., description="The optimized, approved response.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional categorization or origin info.")

class MemorySearchSchema(BaseModel):
    """Schema for searching long-term memory."""
    query: str = Field(..., description="The semantic search query.")
    user_id: str = Field(..., description="The unique identifier for the user.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of memories to retrieve.")

class ContentCuratorSchema(BaseModel):
    """Schema for generating social media briefings."""
    briefing: str = Field(..., description="The raw briefing text or insights.")
    platform: str = Field(..., description="Target platform (facebook, zalo, tiktok, telegram, discord).")
    audience: Optional[str] = Field(default="general", description="Target audience persona.")
    feedback: Optional[str] = Field(default=None, description="Feedback from evaluator for refinement.")

class SystemHealthSchema(BaseModel):
    """Schema for system health checks (no input usually, but good for ACI consistency)."""
    check_type: str = Field(default="full", description="Type of health check (minimal, full).")
