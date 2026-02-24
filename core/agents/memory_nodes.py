"""
Memory Nodes: Context Engineering Utilities
==========================================
Includes nodes for compaction and history management.
"""
from typing import Dict, Any, List
from core.utils.llm_manager import LLMManager

llm = LLMManager()

def memory_compaction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarizes the chat history into a single 'Context Summary' 
    when the message chain gets too long.
    """
    messages = state.get("messages", [])
    token_count = state.get("token_tracker", 0)
    
    # Threshold for compaction: > 15 messages OR > 8000 estimated tokens
    if len(messages) < 15 and token_count < 8000:
        return {}

    print(f"  [Memory] Compacting history ({len(messages)} messages, {token_count} tokens)...")
    
    # Take the last 5 messages to preserve immediate continuity
    preserved_messages = messages[-5:]
    messages_to_summarize = messages[:-5]
    
    context_str = "\n".join(messages_to_summarize)
    
    prompt = f"""
    You are a Memory Manager. Summarize the following agent conversation into a concise 
    'Context Summary' that preserves all key decisions, extracted facts, and pending tasks.
    
    CONVERSATION:
    {context_str}
    
    Format:
    # 🧠 Context Summary
    - **Past Decisions**: ...
    - **Key Facts**: ...
    - **Pending Items**: ...
    """
    
    summary = llm.query(prompt, complexity="L2")
    
    # Return new message list: [Summary, ...Preserved]
    # Note: langgraph custom Reducer (operator.add) will append this.
    # To 'replace' or 'compact', we'd need a different state management approach,
    # but for this system, we label the summary clearly.
    
    compacted_msg = f"System: [MEMORY COMPACTED]\n{summary}"
    
    # Since we use Annotated[List[str], operator.add], we can't easily 'wipe' history
    # without changing the state schema. Instead, we insert the summary.
    return {"messages": [compacted_msg]}
