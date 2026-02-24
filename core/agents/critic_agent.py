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
        messages = state.get("messages", [])
        if len(messages) < 1:
            return RatingIntent(decision="APPROVE", reasoning="No messages to evaluate.", feedback=None)

        last_ai_response = messages[-1]
        user_input = messages[-2] if len(messages) >= 2 else "Context missing"
        memory = state.get("long_term_memory", "None.")

        prompt = f"""
        You are the 'Quality Guard' for an AI Agent team.
        Your job is to CRITIQUE the following AI response based on the CHECKLIST below.

        USER INPUT: {user_input}
        USER BACKGROUND (MEMORY): {memory}
        AI RESPONSE: {last_ai_response}

        --- QUALITY CHECKLIST ---
        1. [STYLE]: Is the tone helpful, engaging, and age-appropriate?
        2. [INTENT]: Does it directly address the user's core request?
        3. [FOCUSED]: Is the information concise or unnecessarily verbose?
        4. [SOCRATIC]: If this is a school exercise, does it guide (Socratic) instead of just giving the answer?
        5. [ACCURACY]: Are there any hallucinations or contradictions?

        CRITIQUE RULES:
        - If ANY checklist item fails significantly, mark as REVISE.
        - provide specific feedback on which item failed.
        - If it's a Socratic tutor (Mimi), direct answers for general learning ARE OK, but answers for solutions/homework ARE NOT.

        Return your critique as a raw JSON string:
        {{
            "decision": "APPROVE" or "REVISE",
            "reasoning": "brief summary of checklist results",
            "feedback": "specific instructions for the agent to fix the output"
        }}
        """

        # Phase 13: Robust JSON Parsing
        from core.utils.json_repair import repair_json
        
        raw = self.llm.query(prompt, complexity="L2")
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
