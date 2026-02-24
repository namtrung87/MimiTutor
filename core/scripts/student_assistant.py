from core.agents.supervisor import build_supervisor_graph
import os

def run_student_assistant():
    print("--- Orchesta Student Assistant (Layer 2) ---")
    print("Type a query. Examples:")
    print("1. 'Extract skill from demo_learning.py'")
    print("2. 'What are the rules for thesis defense?' (needs documents in KnowledgeBase)")
    print("Type 'exit' to quit.")

    app = build_supervisor_graph()

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        # Determine strict inputs for technical path (simple hack for demo)
        input_file = ""
        if "extract" in user_input.lower():
            # Try to find a filename in the query
            words = user_input.split()
            for w in words:
                if "." in w and os.path.exists(w):
                    input_file = w
                    break
        
        initial_state = {
            "messages": [user_input],
            "input_file": input_file, # Optional, used if routed to tech
            "file_content": None,
            "extracted_skill": None,
            "skill_saved": False
        }

        print("--- Agent Thinking ---")
        try:
            for output in app.stream(initial_state):
                for key, value in output.items():
                    # Print only the latest message to keep it clean
                    if "messages" in value:
                        print(f"[{key}]: {value['messages'][-1]}")
        except Exception as e:
            print(f"Error: {e}")
            print("Did you forget to pip install pypdf?")

if __name__ == "__main__":
    run_student_assistant()
