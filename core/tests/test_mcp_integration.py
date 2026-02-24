import sys
import os
import asyncio

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agents.mcp_agent import MCPAgent
from core.state import AgentState

def test_mcp_discovery():
    print("--- Testing MCP Tool Discovery and Execution (Mock Decision) ---")
    
    user_input = "echo 'Hello MCP' using the everything server"
    
    mock_decision = {
        "tool": "echo",
        "args": {"message": "Hello MCP from Mock"}
    }
    
    print("\n--- Running MCP Agent (with Mock Decision) ---")
    try:
        agent = MCPAgent()
        # Directly call process_request with mock
        result_text = asyncio.run(agent.process_request(user_input, mock_decision=mock_decision))
        print(f"Result Message: {result_text}")
        
        if "MCP Result" in result_text and "Hello MCP from Mock" in str(result_text):
            print("\n✅ Verification SUCCESS: MCP Agent discovered and called the tool successfully.")
        else:
            print(f"\n❌ Verification FAILED: Unexpected result format. {result_text}")
    except Exception as e:
        print(f"\n❌ Verification CRASHED: {e}")

if __name__ == "__main__":
    test_mcp_discovery()
