from core.state import AgentState
from core.utils.z_research import ZResearch
from core.utils.mcp_client import MCPClient
from mcp import StdioServerParameters
import asyncio
import os
import json

class MCPAgent:
    """
    Standardized bridge for Model Context Protocol (MCP).
    In a production environment, this would connect to an MCP server (e.g., via stdio or SSE).
    Here, it simulates tool discovery and execution.
    """
    def __init__(self, command: str = "npx", args: list = ["-y", "@modelcontextprotocol/server-everything"]):
        self.researcher = ZResearch()
        self.server_params = StdioServerParameters(command=command, args=args)

    async def _get_tools(self):
        async with MCPClient(self.server_params) as client:
            return await client.list_tools()

    async def process_request(self, question: str, mock_decision: dict = None):
        print(f"  [MCP Agent] Fetching real tools from MCP server...")
        try:
            tools = await self._get_tools()
        except Exception as e:
            print(f"  [MCP Agent] Error listing tools: {e}")
            return f"Error: Could not list tools from MCP server. {e}"

        if mock_decision:
            print(f"  [MCP Agent] Using MOCK Decision: {mock_decision}")
            decision = mock_decision
        else:
            prompt = f"""
            You are an MCP Bridge Agent. You have access to these REAL TOOLS discovered via protocol:
            {json.dumps(tools, indent=2)}
            
            The user wants: {question}
            
            Determine which MCP tool to use and what arguments to provide.
            Return your answer ONLY as a JSON object:
            {{
                "tool": "tool_name",
                "args": {{ "arg1": "val1" }}
            }}
            """
            
            raw_response = self.researcher.query(prompt)
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            
            print(f"  [MCP Agent] Decided Action: {raw_response}")
            try:
                decision = json.loads(raw_response)
            except Exception as e:
                return f"MCP Error (JSON Parse): {e}"
        
        try:
            tool_name = decision.get("tool")
            tool_args = decision.get("args", {})
            
            if tool_name:
                print(f"  [MCP Agent] Executing {tool_name}...")
                async with MCPClient(self.server_params) as client:
                    result = await client.call_tool(tool_name, tool_args)
                    return f"MCP Result: {result}"
            return "MCP Agent: No tool selected or invalid format."
        except Exception as e:
            return f"MCP Error: {e}"

def mcp_agent_node(state: AgentState):
    agent = MCPAgent()
    if state["messages"]:
        question = state["messages"][-1]
        try:
            result = asyncio.run(agent.process_request(question))
            return {"messages": [result]}
        except Exception as e:
            return {"messages": [f"MCP Node Error: {e}"]}
    return {"messages": ["MCP Agent: No request found."]}
