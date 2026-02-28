import os
import sys

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../"))
true_root = os.path.abspath(os.path.join(root_dir, "../"))

for path in [root_dir, true_root]:
    if path not in sys.path:
        sys.path.append(path)

# Set environment variables for the test
os.environ["GEMINI_API_KEY"] = "AIzaSyAkY2PmKjdeqqqlXMH2zEgiJkDzO8PMlKQ"

try:
    from core.agents.mimi_hometutor import build_mimi_graph
    from core.state import AgentState

    graph = build_mimi_graph()
    initial_state = {
        "messages": ["Mimi: Unit 7 Science học những gì"],
        "user_id": "mimi_user",
        "input_file": "",
        "file_content": None,
        "extracted_skill": None,
        "skill_saved": False,
        "routing_category": "mimi"
    }

    print("Invoking graph...")
    results = graph.invoke(initial_state)
    print("Graph execution complete.")
    
    messages = results.get("messages", [])
    print(f"Final response: {messages[-1] if messages else 'No response'}")

except Exception as e:
    import traceback
    print(f"Caught Exception: {e}")
    traceback.print_exc()
