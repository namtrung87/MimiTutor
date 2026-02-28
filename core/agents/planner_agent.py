from core.agents.base_agent import BaseAgent
from core.llm.schemas import ExecutionPlan

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Planner",
            prompt_file="planner_agent",
            default_complexity="L2"
        )

    async def generate_plan(self, user_input: str, context: str = "") -> ExecutionPlan:
        prompt = f"""
        User Request: {user_input}
        Context: {context}
        
        Available Nodes:
        - developer: Code creation/fixing
        - researcher_p: Web research and analysis
        - wellness_node: Health and recovery
        - scholar_tutor: Academic help
        - executive_ops_node: Scheduling and ops
        
        Generate a multi-step plan to solve the request.
        """
        response = self.query_llm(prompt)
        parsed = self.parse_json_response(response)
        return ExecutionPlan(**parsed)
