import asyncio
import json
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from mcp.server.fastmcp import FastMCP
from core.utils.priority_memory import priority_memory
from core.utils.memory_manager import memory_manager
from core.utils.ops_utility import get_system_health_report
from core.utils.z_research import ZResearch
from core.utils.aci_schemas import PriorityMemorySchema, MemorySearchSchema

# Create FastMCP instance
mcp = FastMCP("OrchestraProjectServer")

# Internal modules
research = ZResearch()

@mcp.tool()
def get_priority_answer(question: str) -> str:
    """
    Search for a pre-approved 'golden answer' in the priority memory.
    Useful for fixed system instructions or FAQs.
    """
    print(f"  [MCP Server] get_priority_answer for: {question[:50]}")
    answer = priority_memory.find_priority_answer(question)
    return answer if answer else "No priority answer found."

@mcp.tool()
def search_project_memory(query: str, user_id: str = "default_user", limit: int = 5) -> str:
    """
    Search the long-term project memory for past interactions and distilled facts.
    """
    print(f"  [MCP Server] search_project_memory: {query[:50]}")
    memories = memory_manager.search_memories(query, user_id=user_id, limit=limit)
    if not memories:
        return "No relevant memories found."
    
    formatted = "\n".join([f"- {m.get('text', m.get('memory', ''))}" for m in memories])
    return f"RELEVANT MEMORIES:\n{formatted}"

@mcp.tool()
def get_system_health() -> str:
    """
    Get the current health status of all internal services (Next.js, FastAPI, Ollama).
    """
    print("  [MCP Server] get_system_health")
    report = get_system_health_report()
    return report

@mcp.tool()
def generate_research_strategy(query: str) -> str:
    """
    Generate an optimized research strategy and copy-paste prompt for chat.z.ai.
    """
    print(f"  [MCP Server] generate_research_strategy for: {query}")
    strategy = research.generate_research_strategy(query)
    return json.dumps(strategy, ensure_ascii=False, indent=2)

@mcp.tool()
def ingest_research_results() -> str:
    """
    Read and consolidate manually collected research results from the project folder.
    """
    print("  [MCP Server] ingest_research_results")
    return research.ingest_manual_results()

if __name__ == "__main__":
    # Standard MCP server entry point
    mcp.run()
