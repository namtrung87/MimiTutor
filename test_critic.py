from core.agents.mimi_hometutor import build_mimi_graph
import asyncio

def test_critic():
    print("🚀 Testing Critic Node Integration...")
    
    graph = build_mimi_graph()
    initial_state = {
        "messages": [
            "Mimi: Mẹ bắt làm bài tập Sinh học, chán quá.",
            "System: This is a system message simulating history."
        ],
        "user_id": "test_user",
        "routing_category": "mimi",
        "retry_count": 0
    }
    
    # We will just run the graph and see if it hits critic
    print("Invoking graph...")
    try:
        results = graph.invoke(initial_state)
        print("Graph completed successfully.")
        
        messages = results.get("messages", [])
        critic_hit = any("Critic - " in msg for msg in messages if isinstance(msg, str))
        retry_hit = results.get("retry_count", 0) > 0
        
        if critic_hit:
            print("✅ Critic node was successfully executed in the workflow.")
        else:
            print("❌ Critic node was NOT found in the output messages. Trace failed.")
            
        print(f"Final Retry Count: {results.get('retry_count')}")
            
    except Exception as e:
        print(f"❌ Graph failed to execute: {e}")

if __name__ == "__main__":
    test_critic()
