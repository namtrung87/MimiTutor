import asyncio
from core.agents.executive_ops_agent import ExecutiveOpsAgent

def test_exec_ops():
    agent = ExecutiveOpsAgent()
    user_input = "lịch sinh hoạt hôm nay của tôi gồm những gì"
    print(f"Testing input: '{user_input}'")
    response = agent.process_request(user_input)
    print("\nResponse:")
    print(response)

if __name__ == "__main__":
    test_exec_ops()
