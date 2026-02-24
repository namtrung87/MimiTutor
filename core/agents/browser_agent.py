import asyncio
from browser_use import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from core.state import AgentState
import os

class BrowserAgent:
    """
    Autonomous Web Agent: 
    Uses browser-use to navigate the web, research topics, and extract live data.
    """
    def __init__(self, model_name="models/gemini-3-pro-preview"):
        api_key = os.getenv("GEMINI_API_KEY", "").split(",")[0]
        self.llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)

    async def run_task(self, task_description: str):
        """Executes a browser task autonomously."""
        print(f"  [Browser] Starting autonomous task: {task_description}")
        agent = Agent(
            task=task_description,
            llm=self.llm,
        )
        result = await agent.run()
        return result

def browser_agent_node(state: AgentState):
    """LangGraph node for browser operations."""
    user_input = state["messages"][-1] if state["messages"] else ""
    context = state.get("long_term_memory", [])
    
    # Enrich task description with context
    task = f"Research the following topic: {user_input}. "
    if context:
        task += f"Keep in mind the user's background: {', '.join(context[:3])}."
    
    agent = BrowserAgent()
    # Since LangGraph nodes are typically sync in this version, 
    # we run the async task in an event loop.
    result = asyncio.run(agent.run_task(task))
    
    # browser-use AgentHistory results can be complex; we extract the final result
    final_answer = result.final_result() if hasattr(result, 'final_result') else str(result)
    
    return {
        "browser_results": final_answer,
        "messages": [f"Browser Agent: {final_answer}"]
    }
