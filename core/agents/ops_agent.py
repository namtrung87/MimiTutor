from core.state import AgentState
from core.utils.ops_utility import get_system_health_report, SYSTEM_HEALTH_CONFIG, is_port_open

def ops_node(state: AgentState):
    """
    Proactive Operations Guard:
    Checks system health and warns the user if critical services are down.
    """
    print("  [Ops Guard] Checking system health...")
    
    # 1. Generate health report
    report = get_system_health_report()
    
    # 2. Check for offline services
    offline_services = [info['name'] for port, info in SYSTEM_HEALTH_CONFIG.items() if not is_port_open(port)]
    
    if offline_services:
        warning_msg = f"\n⚠️ [SYSTEM OPS ALERT] These services are currently OFFLINE:\n{report}\n"
        print(f"  [Ops Guard] Detected offline services: {offline_services}")
        
        # Add a system message to the state to alert subsequent agents or the user
        return {"messages": [f"System: [Ops Guard] {warning_msg}"]}
    
    print("  [Ops Guard] System health: OK")
    return {"messages": ["System: [Ops Guard] All services are healthy."]}
