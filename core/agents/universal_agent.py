from core.state import AgentState
from core.vector_store_chroma import ChromaSkillStore
from core.utils.z_research import ZResearch
from core.utils.llm_manager import LLMManager, ContextPruner
from core.utils.mcp_client import MCPClient, quick_mcp_call, StdioServerParameters
import os
import json
import asyncio
from typing import List, Dict, Any

# Optional Imports for Tools
try:
    from langchain_community.tools import DuckDuckGoSearchRun
    ddg_search = DuckDuckGoSearchRun()
except ImportError:
    ddg_search = None

try:
    import yfinance as yf
except ImportError:
    yf = None

class UniversalAgent:
    """
    A production-grade agent that:
    1. Loads a specific system prompt based on 'role'.
    2. Dynamically discovers tools via MCP servers.
    3. Executes via LLM (LLMManager) with standardized ACI.
    """
    def __init__(self):
        self.llm = LLMManager()
        self.max_loops = 3
        # Load MCP Config
        config_path = os.path.join(os.path.dirname(__file__), "../utils/mcp_config.json")
        with open(config_path, "r") as f:
            self.mcp_config = json.load(f)

        self.prompt_map = {
            "research": "research_scholarship_lead",
            "bank": "shadow_bank_consultant",
            "tech": "creative_tech_skill_architect",
            "growth": "growth_branding_specialist",
            "academic": "academic_success_assistant",
            "advisor": "strategic_advisory_consultant",
            "legal": "han_media_legal_guardian",
            "mimi": "mimi_socratic",
            "cos": "executive_chief_of_staff",
            "heritage": "heritage_philosophy_scholar",
            "wellness": "wellness_performance_coach",
            "learning": "personal_intellectual_tutor"
        }

    def _load_system_prompt(self, role: str) -> str:
        filename = self.prompt_map.get(role, "academic_student_success")
        try:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            prompt_path = os.path.join(root_dir, "prompts", f"{filename}.md")
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return f"You are a helpful assistant specialized in {role}."
        except Exception:
            return f"You are a helpful assistant specialized in {role}."

    async def _discover_tools(self) -> List[Dict[str, Any]]:
        """Fetch all available tools from configured MCP servers."""
        all_tools = []
        for server_name, cfg in self.mcp_config["servers"].items():
            try:
                # We limit discovery to avoid prompt bloat, but usually it's fine
                params = StdioServerParameters(command=cfg["command"], args=cfg["args"], env=cfg.get("env", {}))
                async with MCPClient(params) as client:
                    tools = await client.list_tools()
                    for t in tools:
                        t["server"] = server_name # Track origin
                    all_tools.extend(tools)
            except Exception as e:
                print(f"  [UniversalAgent] Failed to discover tools from {server_name}: {e}")
        return all_tools

    async def process_request(self, state: AgentState) -> dict:
        """Standardized ReAct loop using MCP tools."""
        role = state.get("routing_category", "academic")
        messages = state.get("messages", [])
        user_input = messages[-1] if messages else ""
        
        system_prompt = self._load_system_prompt(role)
        
        # Discover Tools
        available_tools = await self._discover_tools()
        tools_str = json.dumps(available_tools, indent=2, ensure_ascii=False) if available_tools else "No tools available."

        tool_instructions = f"""
--- AVAILABLE TOOLS (MCP) ---
{tools_str}

If you need to use a tool, respond with a JSON object:
{{
    "action": "server_name:tool_name",
    "arguments": {{ "arg1": "val1" }}
}}

If you have the final answer, respond normally.
"""

        history = ""
        for i in range(self.max_loops):
            full_prompt = f"{system_prompt}\n{tool_instructions}\n\nUSER: {user_input}\n{history}"
            
            print(f"  [UniversalAgent] executing as {role} (Loop {i})...")
            response = self.llm.query(full_prompt, complexity="L3", domain=role)
            
            if not response:
                return {"messages": [f"{role.capitalize()} Agent: I encountered an error (Empty Response)."]}

            # Check for tool call
            if "{" in response and "\"action\"" in response:
                try:
                    # Clean markdown
                    clean_res = response.strip()
                    if "```json" in clean_res: clean_res = clean_res.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_res: clean_res = clean_res.split("```")[1].split("```")[0].strip()
                    
                    call = json.loads(clean_res)
                    server_tool = call["action"]
                    server_name, tool_name = server_tool.split(":", 1)
                    args = call.get("arguments", {})
                    
                    cfg = self.mcp_config["servers"].get(server_name)
                    if cfg:
                        print(f"  [UniversalAgent] Calling MCP: {server_tool}")
                        result_obj = await quick_mcp_call(cfg["command"], cfg["args"], tool_name, args)
                        
                        # Handle CallToolResult object
                        if hasattr(result_obj, "content"):
                            result_text = "\n".join([c.text for c in result_obj.content if hasattr(c, "text")])
                        else:
                            result_text = str(result_obj)
                            
                        history += f"\nASSISTANT: (Calls {server_tool})\nSYSTEM: {result_text}\n"
                        continue
                except Exception as e:
                    history += f"\nSYSTEM: Error calling tool: {e}\n"
                    continue

            # Final Answer
            return {"messages": [f"{role.capitalize()} Agent: {response}"]}

        return {"messages": [f"{role.capitalize()} Agent: (Tool limit reached) {response}"]}

def universal_agent_node(state: AgentState):
    agent = UniversalAgent()
    return asyncio.run(agent.process_request(state))
