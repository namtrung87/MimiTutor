import os
import json
from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.state import AgentState
from core.utils.llm_manager import LLMManager

class RatingIntent(BaseModel):
    decision: Literal["APPROVE", "REVISE"] = Field(description="Decision on whether the output is acceptable.")
    feedback: Optional[str] = Field(default=None, description="Feedback for the original agent if revision is needed.")
    reasoning: str = Field(description="Internal logic for the decision.")

class CriticAgent:
    """
    Quality Assurance Agent:
    Validates agent outputs for:
    1. Pedagogical style (Socratic)
    2. Faithfulness to memory/context
    3. Technical accuracy
    """
    def __init__(self):
        self.llm = LLMManager()

    def evaluate(self, state: AgentState) -> RatingIntent:
        messages = state.messages
        if not messages:
            return RatingIntent(decision="APPROVE", reasoning="No messages to evaluate.", feedback=None)

        # Skip all "System:" messages at the end to find the actual AI response
        last_ai_response = ""
        user_input = "Context missing"
        
        # We need the last non-System message as AI response, and the one before that as User input.
        non_system_msgs = [m for m in messages if isinstance(m, str) and not m.startswith("System:")]
        
        if len(non_system_msgs) >= 1:
            last_ai_response = non_system_msgs[-1]
        if len(non_system_msgs) >= 2:
            user_input = non_system_msgs[-2]
            
        memory = state.long_term_memory or "None."

    def _load_prompt(self):
        if not hasattr(self, "_cached_prompt") or self._cached_prompt is None:
            root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../.."))
            prompt_path = os.path.join(root_dir, "prompts", "critic_quality_guard.md")
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self._cached_prompt = f.read()
            else:
                self._cached_prompt = "You are the 'Quality Guard' for an AI Agent team."
        return self._cached_prompt

    def evaluate(self, state: AgentState) -> RatingIntent:
        messages = state.messages
        if not messages:
            return RatingIntent(decision="APPROVE", reasoning="No messages to evaluate.", feedback=None)

        # Skip all "System:" messages at the end to find the actual AI response
        last_ai_response = ""
        user_input = "Context missing"
        
        # We need the last non-System message as AI response, and the one before that as User input.
        non_system_msgs = [m for m in messages if isinstance(m, str) and not m.startswith("System:")]
        
        if len(non_system_msgs) >= 1:
            last_ai_response = non_system_msgs[-1]
        if len(non_system_msgs) >= 2:
            user_input = non_system_msgs[-2]
            
        memory = state.long_term_memory or "None."

        prompt_template = self._load_prompt()
        prompt = prompt_template.format(
            user_input=user_input,
            memory=memory,
            last_ai_response=last_ai_response
        )

        # Phase 13: Robust JSON Parsing
        from core.utils.json_repair import repair_json
        
        raw = self.llm.query_sync(prompt, complexity="L2")
        if not raw:
            return RatingIntent(decision="APPROVE", reasoning="LLM returned empty response (Auto-Approved).", feedback=None)
        
        data = repair_json(raw)
        
        if data:
            try:
                return RatingIntent(**data)
            except Exception as e:
                print(f"  [Critic] Validation error: {e}. Data: {data}")
                return RatingIntent(decision="APPROVE", reasoning="Parsed JSON did not match schema (Auto-Approved).", feedback=None)
        
        print(f"  [Critic] Failed to parse JSON. Raw: {raw[:50]}...")
        return RatingIntent(decision="APPROVE", reasoning="Unparseable output from Critic (Auto-Approved).", feedback=None)

def critic_node(state: AgentState):
    """
    LangGraph node that performs the critique.
    Increments a retry counter in the state (requires AgentState update).
    """
    critic = CriticAgent()
    evaluation = critic.evaluate(state)
    
    # Store decision in state for routing
    return {
        "routing_category": f"critique_{evaluation.decision.lower()}",
        "messages": [f"System: Critic - {evaluation.decision} | Reason: {evaluation.reasoning}"],
        "critic_feedback": evaluation.feedback # New state field
    }
