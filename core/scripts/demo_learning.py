import os

def demo_self_learning_graph():
    print("--- Initializing LangGraph Agent ---")
    
    # Check for dependencies
    try:
        import langgraph
        import chromadb
        from core.graph import build_graph
    except ImportError as e:
        print(f"CRITICAL: Missing dependency: {e}")
        print("Please run: pip install langgraph langchain langchain-community chromadb")
        return

    # Build the graph
    app = build_graph()
    
    # Define input
    reference_file = "05_Gamification_Projects/mom-game/src/components/Level1.jsx"
    
    # Run the graph
    print(f"--- Running Graph on: {reference_file} ---")
    
    inputs = {"input_file": reference_file, "messages": []}
    
    # Run and stream output with safety limit
    config = {"recursion_limit": 10}
    for output in app.stream(inputs, config=config):
        for key, value in output.items():
            print(f"Node '{key}':")
            # print(f"  State: {value}") # Verbose
            if "messages" in value:
                print(f"  Log: {value['messages']}")

    print("\n--- Graph Execution Complete ---")

if __name__ == "__main__":
    demo_self_learning_graph()
