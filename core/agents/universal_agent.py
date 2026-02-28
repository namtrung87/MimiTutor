from core.state import AgentState
from core.vector_store_chroma import ChromaSkillStore
from core.utils.z_research import ZResearch
from core.utils.llm_manager import LLMManager, ContextPruner
from core.utils.mcp_client import MCPClient, quick_mcp_call, StdioServerParameters
import os
import json
import asyncio
from typing import List, Dict, Any, Optional

class UniversalAgent:
    """
    A production-grade agent that:
    1. Loads a specific system prompt based on 'role'.
    2. Dynamically discovers tools via MCP servers.
    3. Executes via LLM (LLMManager) with standardized ACI.
    """
    _ddg_search = None
    _yf = None

    @classmethod
    def get_ddg_search(cls):
        """Lazy-load DuckDuckGoSearchRun."""
        if cls._ddg_search is None:
            try:
                from langchain_community.tools import DuckDuckGoSearchRun
                cls._ddg_search = DuckDuckGoSearchRun()
            except ImportError:
                cls._ddg_search = False # Mark as not available
        return cls._ddg_search if cls._ddg_search is not False else None

    @classmethod
    def get_yfinance(cls):
        """Lazy-load yfinance."""
        if cls._yf is None:
            try:
                import yfinance as yf
                cls._yf = yf
            except ImportError:
                cls._yf = False
        return cls._yf if cls._yf is not False else None
    def __init__(self) -> None:
        """
        Initializes the Universal Agent with an LLMManager, default settings,
        and dynamically loads MCP and Gems configurations.
        """
        self.llm = LLMManager()
        self.max_loops: int = 3
        
        # Load MCP Config
        config_path = os.path.join(os.path.dirname(__file__), "../utils/mcp_config.json")
        with open(config_path, "r") as f:
            self.mcp_config = json.load(f)

        # Load Gems Config
        gems_path = os.path.join(os.path.dirname(__file__), "../utils/gems_config.json")
        try:
            with open(gems_path, "r", encoding="utf-8") as f:
                self.gems_config = json.load(f).get("gems", {})
        except Exception as e:
            print(f"  [UniversalAgent] Warning: Failed to load gems_config.json: {e}")
            self.gems_config = {}

    def _load_system_prompt(self, role: str) -> str:
        """
        Loads the system prompt from disk based on the Gem role.
        """
        gem = self.gems_config.get(role, {})
        filename = gem.get("system_prompt", "academic_student_success.md")
        
        try:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            prompt_path = os.path.join(root_dir, "prompts", filename)
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return f"You are a helpful assistant specialized in {role}."
        except Exception:
            return f"You are a helpful assistant specialized in {role}."

    async def _discover_tools(self) -> List[Dict[str, Any]]:
        """Fetch all available tools from configured MCP servers concurrently with timeout."""
        all_tools = []
        
        async def fetch_from_server(server_name, cfg):
            try:
                params = StdioServerParameters(command=cfg["command"], args=cfg["args"], env=cfg.get("env", {}))
                # Adding 10s timeout per server to prevent total hang
                async with asyncio.timeout(10.0):
                    async with MCPClient(params) as client:
                        tools = await client.list_tools()
                        for t in tools:
                            t["server"] = server_name
                        return tools
            except Exception as e:
                print(f"  [UniversalAgent] Failed to discover tools from {server_name}: {e}")
                return []

        tasks = [fetch_from_server(name, cfg) for name, cfg in self.mcp_config["servers"].items()]
        results = await asyncio.gather(*tasks)
        
        for r in results:
            all_tools.extend(r)
            
        return all_tools

    async def process_request(self, state: AgentState) -> Dict[str, Any]:
        """
        Standardized ReAct loop using native Gemini Tool Calling and Gem-specific grounding.
        """
        role: str = state.get("routing_category", "academic")
        messages = state.get("messages", [])
        user_input = messages[-1] if messages else ""
        
        # Load Gem Configuration
        gem = self.gems_config.get(role, {})
        system_prompt = self._load_system_prompt(role)
        target_model = gem.get("model")
        use_search = gem.get("grounding") == "google_search"
        
        # Discover Tools
        available_tools = await self._discover_tools()
        
        history = []
        flat_history = ""

        for i in range(self.max_loops):
            print(f"  [UniversalAgent] executing Gem '{gem.get('name', role)}' (Loop {i})...")
            
            # Use query_tools for the specialized ReAct behavior
            # Note: query_tools currently does not support grounding directly in LLMManager, 
            # we might need to use query for simple grounding if no tools are needed,
            # but for now we follow the existing tool-calling flow.
            # We'll prioritize tool-calling for these high-end agents.
            
            response = self.llm.query_tools(
                prompt=f"{system_prompt}\n\nCONTEXT:\n{flat_history}\n\nUSER: {user_input}",
                tools=available_tools,
                complexity="L3" if role != "academic" else "L2",
                model_override=target_model,
                domain=role
            )
            
            if not response:
                # Fallback to simple query if tool query fails or if grounding is needed without tools
                if use_search:
                     print(f"  [UniversalAgent] Falling back to search-grounded query for Gem '{role}'")
                     final_text = self.llm.query(
                         prompt=f"{system_prompt}\n\nUSER: {user_input}",
                         complexity="L2",
                         use_google_search=True,
                         domain=role
                     )
                     return {"messages": [f"{gem.get('name', role.capitalize())}: {final_text}"]}
                
                return {"messages": [f"{gem.get('name', role.capitalize())}: I encountered an error (Empty Response)."]}

            # Handle Native Response Object (Gemini style)
            has_call = False
            # Check if it's a GenerateContentResponse or a string
            if hasattr(response, "candidates"):
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        has_call = True
                        tool_name = part.function_call.name
                        args = dict(part.function_call.args)
                        
                        print(f"  [UniversalAgent] Gem '{role}' Tool Call: {tool_name}")
                        
                        target_tool = tool_name
                        server_name = None
                        for t in available_tools:
                            if t["name"] == tool_name:
                                server_name = t.get("server")
                                break
                        
                        if server_name:
                            cfg = self.mcp_config["servers"].get(server_name)
                            if cfg:
                                result_obj = await quick_mcp_call(cfg["command"], cfg["args"], tool_name, args)
                                if hasattr(result_obj, "content"):
                                    result_text = "\n".join([c.text for c in result_obj.content if hasattr(c, "text")])
                                else:
                                    result_text = str(result_obj)
                                flat_history += f"\n- THOUGHT: Using {tool_name}\n- OBSERVATION: {result_text}\n"
                        else:
                            flat_history += f"\n- SYSTEM ERROR: Tool {tool_name} not found in registry.\n"
                
                if has_call:
                    continue

                final_text = response.text
            else:
                # If it's just a string (fallback case)
                final_text = str(response)

            return {"messages": [f"{gem.get('name', role.capitalize())}: {final_text}"]}

        return {"messages": [f"{gem.get('name', role.capitalize())}: (Reached limit) {final_text}"]}

def universal_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node wrapper for the UniversalAgent.
    
    Args:
        state (AgentState): The graph state.
        
    Returns:
        Dict[str, Any]: The result state dictionary.
    """
    agent = UniversalAgent()
    return asyncio.run(agent.process_request(state))
