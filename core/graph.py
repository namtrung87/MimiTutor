import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from core.state import AgentState
import os
import json

_store = None
_checkpointer = None

def _get_checkpointer():
    """Lazily initialize the SQLite checkpointer."""
    global _checkpointer
    if _checkpointer is None:
        conn = sqlite3.connect("orchesta_checkpoints.db", check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
    return _checkpointer

def _get_store():
    """Lazy-load ChromaSkillStore to avoid slow imports at startup."""
    global _store
    if _store is None:
        from core.vector_store_chroma import ChromaSkillStore
        try:
            print("  [Graph] Initializing ChromaSkillStore...")
            _store = ChromaSkillStore()
        except Exception as e:
            print(f"  [Graph] Warning: Could not initialize ChromaDB: {e}")
            _store = None
    return _store

# Initialize tools
def _get_llm():
    from core.mock_llm import MockLLM
    return MockLLM()

def load_file_node(state: AgentState):
    """Reads the file content."""
    file_path = state["input_file"]
    print(f"  [Graph] Loading file: {file_path}")
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"file_content": content, "messages": ["File loaded successfully"]}
    else:
        return {"file_content": None, "messages": ["File not found"]}

def extract_skill_node(state: AgentState):
    """Extracts skill using LLM."""
    content = state.get("file_content")
    if not content:
        return {"extracted_skill": None}
    
    retry_count = state.get("retry_count", 0)
    print(f"  [Graph] Extracting skill... (Attempt {retry_count + 1})")
    
    # Context Reset for retries
    if retry_count > 0:
        previous_feedback = state.get("critic_feedback", "Previous attempts failed.")
        print("  [Graph] Providing context reset for retry.")
        content = f"{content}\n\n[CONTEXT RESET: This is retry {retry_count + 1}. Feedback: {previous_feedback}. DO NOT repeat previous mistakes. Try a completely new approach.]"

    # Simulate LLM extraction
    # In real world: messages = [SystemMessage(...), HumanMessage(content)]
    # response = model.invoke(messages)
    llm = _get_llm()
    skill = llm.extract_skill(content)
    # Inject source file info
    skill["source_file"] = state["input_file"]
    
    return {
        "extracted_skill": skill, 
        "messages": [f"Extracted skill: {skill['title']} (Attempt {retry_count + 1})"]
    }

def save_skill_node(state: AgentState):
    """Saves the extraction to Vector Store."""
    skill = state.get("extracted_skill")
    store = _get_store()
    if skill and store:
        print(f"  [Graph] Saving skill: {skill['title']}")
        store.add_skill(skill)
        return {"skill_saved": True, "messages": ["Skill saved to ChromaDB"]}
    return {"skill_saved": False, "messages": ["Failed to save skill"]}

def validate_skill_node(state: AgentState):
    """
    Judges the quality of the extraction using a fast LLM Judge.
    """
    skill = state.get("extracted_skill")
    retry_count = state.get("retry_count", 0)
    
    print(f"  [Graph] Validating skill with LLM Judge... (Attempt {retry_count + 1})")
    
    if not skill:
        return {"is_valid": False, "messages": ["No skill data to validate"]}
    
    from core.utils.z_research import ZResearch
    judge = ZResearch()
    
    prompt = f"""
    You are a Quality Assurance Judge. Evaluate the following extracted skill for completeness and accuracy.
    
    Skill: {json.dumps(skill, indent=2)}
    
    Criteria:
    1. Title must be professional and concise.
    2. Logic summary must be technically sound and cover the main functions.
    3. Dependencies must be listed if any are present in the logic.

    If the skill is high quality, respond with: VALID
    If not, respond with: INVALID: [BRIEF FEEDBACK]
    """
    
    # Use 'fast' model for validation
    response = judge.query(prompt, complexity="fast")
    
    if "VALID" in response.upper() and "INVALID" not in response.upper():
        return {"is_valid": True, "messages": ["Extraction validated by AI Judge"]}
    else:
        feedback = response.replace("INVALID:", "").strip()
        return {
            "is_valid": False, 
            "retry_count": retry_count + 1,
            "critic_feedback": feedback,
            "messages": [f"AI Judge Feedback: {feedback}"]
        }

def build_graph(persist: bool = True):
    """Constructs the compiled graph with self-correction and optional persistence."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("load_file", load_file_node)
    workflow.add_node("extract_skill", extract_skill_node)
    workflow.add_node("validate_skill", validate_skill_node)
    workflow.add_node("save_skill", save_skill_node)

    workflow.set_entry_point("load_file")

    # Edges
    workflow.add_edge("load_file", "extract_skill")
    workflow.add_edge("extract_skill", "validate_skill")
    
    # Conditional edge for self-correction
    def should_continue(state):
        if state.get("is_valid") is True:
            return "save"
        
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if retry_count >= max_retries:
            print(f"  [Graph] Max retries ({max_retries}) reached. Saving as-is.")
            return "save"
            
        return "retry"

    workflow.add_conditional_edges(
        "validate_skill",
        should_continue,
        {
            "save": "save_skill",
            "retry": "extract_skill"
        }
    )
    
    workflow.add_edge("save_skill", END)

    # Compile with checkpointer for durable state
    checkpointer = _get_checkpointer() if persist else None
    return workflow.compile(checkpointer=checkpointer)
