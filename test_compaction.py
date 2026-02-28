from core.state import AgentState, messages_reducer
from core.agents.memory_nodes import memory_compaction_node

def test_compaction():
    print("🚀 Testing Memory Compaction with Custom Reducer...")
    
    state = {
        "messages": [f"Message {i}" for i in range(20)],
        "token_tracker": 9000
    }
    
    print(f"Initial message count: {len(state['messages'])}")
    
    # Simulate LangGraph call
    update = memory_compaction_node(state)
    
    if "messages" in update and isinstance(update["messages"], dict):
        # Manually apply the reducer as LangGraph would
        new_messages = messages_reducer(state["messages"], update["messages"])
        print(f"New message count after compaction: {len(new_messages)}")
        print(f"First message: {new_messages[0]}")
        
        if len(new_messages) == 6: # 1 summary + 5 preserved
            print("✅ Compaction SUCCESS: History trimmed correctly.")
        else:
            print(f"❌ Compaction FAILED: Expected 6 messages, got {len(new_messages)}.")
    else:
        print("❌ Compaction FAILED: memory_compaction_node did not return expected replace signal.")

if __name__ == "__main__":
    test_compaction()
