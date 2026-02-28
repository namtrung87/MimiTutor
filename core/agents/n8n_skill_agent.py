import os
import json
import httpx
from core.state import AgentState
from core.utils.llm_manager import LLMManager

class N8NSkillAgent:
    """
    Routes specialized skill requests (Calendar, Notion, etc.) to n8n webhooks.
    This replaces complex Python-based integrations with visual n8n flows.
    """
    def __init__(self):
        self.llm = LLMManager()
        self.n8n_webhook_url = os.getenv("N8N_SKILL_WEBHOOK_URL")

    async def execute(self, state: AgentState) -> dict:
        user_input = state["messages"][-1] if state["messages"] else ""
        role = state.get("routing_category", "general")
        
        print(f"  [n8n Skill Agent] Analyzing request: {user_input[:50]}...")

    def _get_prompt(self):
        if not hasattr(self, "_cached_prompt") or self._cached_prompt is None:
            root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../.."))
            prompt_path = os.path.join(root_dir, "prompts", "n8n_skill_extraction.md")
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self._cached_prompt = f.read()
            else:
                self._cached_prompt = "Extract action and params for automation."
        return self._cached_prompt

    async def execute(self, state: AgentState) -> dict:
        user_input = state["messages"][-1] if state["messages"] else ""
        role = state.get("routing_category", "general")
        
        print(f"  [n8n Skill Agent] Analyzing request: {user_input[:50]}...")

        # 1. First, use LLM to extract structured data for the n8n webhook
        prompt_template = self._get_prompt()
        prompt = prompt_template.format(user_input=user_input, role=role)
        
        try:
            raw_response = self.llm.query(prompt, complexity="L2")
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            
            payload = json.loads(raw_response)
            
            # 2. Call n8n Webhook
            if not self.n8n_webhook_url:
                return {"messages": ["n8n Skill Agent: Missing N8N_SKILL_WEBHOOK_URL. Simulation mode active."], "data": payload}

            print(f"  [n8n Skill Agent] Calling n8n: {payload['action']}")
            async with httpx.AsyncClient() as client:
                response = await client.post(self.n8n_webhook_url, json=payload, timeout=30.0)
                response.raise_for_status()
                n8n_result = response.json()
            
            return {
                "messages": [f"n8n Skill Agent: Processed '{payload['action']}'. Result: {n8n_result.get('message', 'Success')}"],
                "data": n8n_result
            }

        except Exception as e:
            print(f"  [n8n Skill Agent] Proxy Error: {e}")
            return {"messages": [f"n8n Skill Agent: I encountered an error while delegating to n8n: {str(e)}"]}

def n8n_skill_node(state: AgentState):
    agent = N8NSkillAgent()
    # LangGraph usually runs nodes in a thread pool if they are sync, 
    # but since this uses httpx it's better to run async correctly.
    # We'll use asyncio.run if called from a sync context or assume async graph for ainvoke.
    import asyncio
    try:
        # Check if we are already in an event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In LangGraph ainvoke, this is fine
            return loop.create_task(agent.execute(state))
        else:
            return asyncio.run(agent.execute(state))
    except Exception:
         # Fallback for sync execution in basic LangGraph
         return asyncio.run(agent.execute(state))
