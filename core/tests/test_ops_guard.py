import sys
import os

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.utils.ops_utility import is_port_open, get_system_health_report
from core.agents.ops_agent import ops_node
from core.state import AgentState

def test_ops_logic():
    print("--- Testing Ops Logic ---")
    # This just prints the current state of your system
    print(get_system_health_report())
    
    # We can mock a state and run the node
    mock_state: AgentState = {
        "messages": ["User: Hello"],
        "user_id": "test_user"
    }
    
    print("\n--- Running Ops Node ---")
    result = ops_node(mock_state)
    print(f"Result Messages: {result['messages']}")
    
    if any("OFFLINE" in m for m in result['messages']):
        print("\n✅ Verification SUCCESS: Ops Guard detected offline services and issued a warning.")
    else:
        print("\nℹ️ Verification INFO: All services appear to be ONLINE. Try stopping a service (like npm run dev) to see the alert.")

if __name__ == "__main__":
    test_ops_logic()
