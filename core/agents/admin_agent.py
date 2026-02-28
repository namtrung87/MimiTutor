from core.agents.universal_agent import universal_agent_node
from core.state import AgentState

def admin_agent_node(state: AgentState):
    """
    Administrative & Procure-Ops Node.
    Uses the specialized 'admin_procure_ops' prompt for all operations.
    """
    print("  [Admin Agent] Handling administrative/procurement request...")
    # We pass the persona key explicitly to the universal_agent_node logic via the routing_category
    # Or we can just call it directly with a modified state if needed.
    # In this architecture, universal_agent_node looks up the prompt in the supervisor's prompt dictionary.
    
    return universal_agent_node(state)
