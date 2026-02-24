from typing import Literal
from pydantic import BaseModel
from core.state import AgentState
from core.utils.llm_manager import LLMManager

class IntentClassification(BaseModel):
    intent: Literal["THEORY", "EXERCISE", "GENERAL"]
    reason: str

class MimiRouter:
    def __init__(self):
        self.llm = LLMManager()

    def classify_intent(self, user_input: str) -> IntentClassification:
        """
        Classifies Mimi's input into Theory (Learning/Concepts) or Exercise (Doing homework/Problems).
        """
        system_prompt = """
        You are a fast router for Mimi's SECONDARY SCIENCE AI. 
        Mimi is studying Grade 7 Science (Cambridge).
        
        Classify the user input into:
        - THEORY: If the child asks "What is...", "Explain...", "How does... work", or wants general Science knowledge (cells, chemistry, physics).
        - EXERCISE: If the child asks for help with a specific Science problem, "Solve this experiment", "How to do Exercise 1 in Science unit", or provides a Science task.
        - GENERAL: Greetings, casual chat, or non-Science topics.
        
        Respond ONLY with JSON matching the schema.
        """
        
        prompt = f"USER INPUT: {user_input}"
        
        try:
            # Use a faster/cheaper model for routing (L1)
            response = self.llm.query(f"{system_prompt}\n\n{prompt}", complexity="L1")
            
            # Basic cleanup if LLM includes markdown
            if "```json" in response:
                response = response.split("```json")[-1].split("```")[0].strip()
            
            import json
            data = json.loads(response)
            return IntentClassification(**data)
        except Exception as e:
            print(f"  [MimiRouter] Routing error: {e}. Falling back to rule-based.")
            return self._rule_based_fallback(user_input)

    def _rule_based_fallback(self, user_input: str) -> IntentClassification:
        ui = user_input.lower()
        exercise_keywords = ["giải", "đáp án", "kết quả", "bài tập", "bài 1", "bài 2", "solve", "answer", "exercise", "=", "+", "-", "x", "/", "phương trình"]
        if any(w in ui for w in exercise_keywords):
            return IntentClassification(intent="EXERCISE", reason="Rule-based: Exercise keywords detected.")
        
        theory_keywords = ["là gì", "tóm tắt", "giảng", "giải thích", "explain", "summarize", "concept", "ý nghĩa", "tại sao"]
        if any(w in ui for w in theory_keywords):
            return IntentClassification(intent="THEORY", reason="Rule-based: Theory keywords detected.")
            
        return IntentClassification(intent="GENERAL", reason="Rule-based: Defaulting to General.")

def mimi_router_node(state: AgentState):
    """
    LangGraph node that routes Mimi's input to the correct specialized agent.
    """
    messages = state.get("messages", [])
    user_input = ""
    for msg in reversed(messages):
        if msg and isinstance(msg, str) and not msg.startswith("System"):
            user_input = msg
            break
            
    if not user_input:
        user_input = messages[-1] if messages else ""
        
    router = MimiRouter()
    classification = router.classify_intent(user_input)
    print(f"  [MimiRouter] Intent: {classification.intent} ({classification.reason})")
    
    # We store the classification in the state to guide LangGraph routing
    return {"routing_category": f"mimi_{classification.intent.lower()}"}
