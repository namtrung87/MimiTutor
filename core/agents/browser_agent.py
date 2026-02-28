import asyncio
import os
from browser_use import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from core.state import AgentState
from core.agents.base_agent import BaseAgent
from core.utils.error_handler import with_agent_fallback

class BrowserAgent(BaseAgent):
    """
    Autonomous Web Agent: 
    Uses browser-use to navigate the web, research topics, and extract live data.
    """
    name = "browser_agent"
    domain = "research"
    default_complexity = "L2"

    def __init__(self, model_name="models/gemini-2.0-flash"):
        super().__init__()
        api_key = os.getenv("GEMINI_API_KEY", "").split(",")[0]
        self.browser_llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)

    async def run_browser_task(self, task_description: str):
        """Executes a browser task autonomously."""
        print(f"  [Browser] Starting autonomous task: {task_description}")
        agent = Agent(
            task=task_description,
            llm=self.browser_llm,
        )
        result = await agent.run()
        return result

    def process_request(self, state: AgentState) -> dict:
        user_input = self.extract_user_input(state)
        context = state.get("long_term_memory", [])
        
        # Enrich task description with context
        task = f"Research the following topic: {user_input}. "
        if context:
            task += f"Keep in mind the user's background: {', '.join(context[:3])}."
        
        # browser-use is inherently async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                result = loop.run_until_complete(self.run_browser_task(task))
            else:
                result = loop.run_until_complete(self.run_browser_task(task))
        except RuntimeError:
            result = asyncio.run(self.run_browser_task(task))
        
        final_answer = result.final_result() if hasattr(result, 'final_result') else str(result)
        
        return {
            "browser_results": final_answer,
            "messages": [f"Browser Agent: {final_answer}"]
        }

@with_agent_fallback()
def browser_agent_node(state: AgentState):
    agent = BrowserAgent()
    return agent.process_request(state)
