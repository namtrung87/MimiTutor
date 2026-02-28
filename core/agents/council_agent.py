import asyncio
from typing import Dict, Any
from core.state import AgentState
from core.services.council_service import CouncilService
from core.agents.base_agent import BaseAgent
from core.utils.error_handler import with_agent_fallback
from core.utils.bot_logger import get_logger

logger = get_logger("council_agent")

class CouncilAgent(BaseAgent):
    """
    Agent that invokes the Council deliberation process for complex queries.
    """
    name = "council_agent"
    domain = "council"
    default_complexity = "L3"

    async def deliberate_async(self, user_input: str, tier: str) -> str:
        service = CouncilService()
        return await service.deliberate(user_input, council_tier=tier)

    def process_request(self, state: AgentState) -> Dict[str, Any]:
        user_input = self.extract_user_input(state)
        
        # Determine tier based on routing category or complexity
        tier = state.get("council_tier", "fast")
        if any(kw in user_input.lower() for kw in ["elite", "chuyên gia", "tổng lực", "phức tạp"]):
            tier = "elite"
            
        logger.info(f"Council Agent activated for query: {user_input[:50]}... (Tier: {tier})")
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                final_response = loop.run_until_complete(self.deliberate_async(user_input, tier))
            else:
                final_response = loop.run_until_complete(self.deliberate_async(user_input, tier))
        except RuntimeError:
            final_response = asyncio.run(self.deliberate_async(user_input, tier))
        
        return {
            "messages": [f"LLM Council: {final_response}"],
            "execution_status": "success"
        }

@with_agent_fallback()
def council_agent_node(state: AgentState) -> Dict[str, Any]:
    agent = CouncilAgent()
    return agent.process_request(state)
