from core.state import AgentState
from core.utils.ops_utility import get_system_health_report, SYSTEM_HEALTH_CONFIG, is_port_open
from core.agents.base_agent import BaseAgent
from core.utils.error_handler import with_agent_fallback

class OpsAgent(BaseAgent):
    """
    Proactive Operations Guard:
    1. Checks system health.
    2. Validates user input against safety guardrails.
    """
    name = "ops_agent"
    domain = "tech"
    default_complexity = "L1"

    def run_guardrails(self, text: str) -> bool:
        """
        Uses a specialized safety model to check for unsafe content.
        """
        prompt = f"""
        [INST] Task: Check if there is unsafe content in 'User Prompt' below.
        <User Prompt>
        {text}
        </User Prompt>
        
        Answer only 'safe' or 'unsafe'. [/INST]
        """
        response = self.query_llm(prompt, complexity="L1").lower()
        return "unsafe" not in response

    def process_request(self, state: AgentState) -> dict:
        print("  [Ops Guard] Checking system health and safety...")
        
        # 1. Safety Check (Guardrails)
        user_input = self.extract_user_input(state)
        if user_input and not self.run_guardrails(user_input):
            return {
                "messages": ["System: [Ops Guard] ⚠️ Security Alert: Potential prompt injection or unsafe content detected. Request blocked."],
                "routing_category": "ethics"
            }

        # 2. Generate health report
        report = get_system_health_report()
        offline_services = [info['name'] for port, info in SYSTEM_HEALTH_CONFIG.items() if not is_port_open(port)]
        
        if offline_services:
            warning_msg = f"\n⚠️ [SYSTEM OPS ALERT] These services are currently OFFLINE:\n{report}\n"
            return {"messages": [f"System: [Ops Guard] {warning_msg}"]}
        
        return {"messages": ["System: [Ops Guard] All systems green."]}

@with_agent_fallback()
def ops_node(state: AgentState):
    agent = OpsAgent()
    return agent.process_request(state)
