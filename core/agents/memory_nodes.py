"""
Memory Nodes: Context Engineering & Long-term Storage
===================================================
Includes nodes for real-time fact extraction and long-term memory integration.
"""
from typing import Dict, Any, List
from core.services.memory_service import memory_service

def memory_compaction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automated Fact Extraction:
    Extracts core facts from the current interaction and saves to Mem0.
    """
    messages = state.get("messages", [])
    user_id = state.get("user_id", "default_user")
    
    if not messages:
        return {}

    # Extract the last few messages to identify facts
    # In a real workflow, we might only do this periodically or upon task completion
    last_interaction = "\n".join(messages[-2:])
    
    print(f"  [Memory] Auto-extracting facts for user {user_id}...")
    
    try:
        # Mem0 handles the extraction and storage internally
        memory_service.add_memory(user_id=user_id, text=last_interaction)
        return {"messages": ["System: [Memory] Facts extracted and saved to long-term memory."]}
    except Exception as e:
        print(f"  [Memory] Warning: Fact extraction failed: {e}")
        return {}

def memory_retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves relevant user facts from Mem0 to inject into the current context.
    """
    user_id = state.get("user_id", "default_user")
    messages = state.get("messages", [])
    
    if not messages:
        return {}
        
    query = messages[-1]
    print(f"  [Memory] Retrieving facts for: {query[:50]}...")
    
    try:
        memories = memory_service.search_memory(user_id=user_id, query=query)
        facts = [m['memory'] for m in memories]
        
        if facts:
            fact_str = "\n".join([f"- {f}" for f in facts])
            return {
                "long_term_memory": facts,
                "messages": [f"System: [Memory] Retrieved context: {fact_str[:100]}..."]
            }
    except Exception as e:
        print(f"  [Memory] Warning: Retrieval failed: {e}")
        
    return {}
