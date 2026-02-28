from core.agents.base_agent import BaseAgent
from core.llm.schemas import ReflectionLog

class ReflectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Reflection",
            prompt_file="reflection_agent",
            default_complexity="L1"
        )

    async def reflect(self, interaction_json: str) -> ReflectionLog:
        prompt = f"""
        Analyze the following interaction and determine if it was successful.
        Identify any permanent facts about the user's preferences or "lessons learned" for future tasks.
        
        Interaction:
        {interaction_json}
        """
        response = self.query_llm(prompt)
        parsed = self.parse_json_response(response)
        return ReflectionLog(**parsed)
