import sys
import asyncio
from core.agents.supervisor import build_supervisor_graph
from core.state import AgentState

def delegate_task(prompt: str):
    """
    Delegates a task to the internal Supervisor Agent graph.
    """
    print(f"\n[Delegate] Delegating task: {prompt}")
    
    # Initialize the graph
    app = build_supervisor_graph()
    
    # Initialize state
    initial_state: AgentState = {
        "messages": [prompt],
        "routing_category": "",
        "long_term_memory": [],
        "retry_count": 0,
        "user_id": "antigravity_delegate"
    }
    
    print("[Delegate] Running supervisor graph...")
    
    # Run the graph
    # LangGraph compiled app.invoke is synchronous if nodes are synchronous
    # supervisor.py nodes are mostly synchronous for now
    result = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("DELEGATION RESULT")
    print("="*50)
    print(f"Category: {result.get('routing_category')}")
    
    if result.get("messages"):
        # The last message is usually the response
        last_msg = result["messages"][-1]
        print(f"\nResponse:\n{last_msg}")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python core/utils/delegate.py \"your prompt here\"")
    else:
        user_prompt = " ".join(sys.argv[1:])
        delegate_task(user_prompt)
