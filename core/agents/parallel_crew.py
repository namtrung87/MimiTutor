from core.state import AgentState
from core.utils.llm_manager import LLMManager
from typing import Dict, List, Any
import json

llm = LLMManager()

class PerspectiveAgent:
    def __init__(self, role_name: str, mission: str, domain: str = "general"):
        self.role_name = role_name
        self.mission = mission
        self.domain = domain

    def run(self, state: AgentState) -> Dict[str, Any]:
        user_input = state["messages"][-1] if state.get("messages") else "MISSING"
        memory = state.get("long_term_memory", [])
        print(f"  [DEBUG] PerspectiveAgent({self.role_name}): input={user_input[:20]}...")
        
        prompt = f"""
        You are a {self.role_name}.
        MISSION: {self.mission}
        
        USER REQUEST: {user_input}
        CONTEXT/MEMORY: {memory}
        
        Provide your specialized perspective based on your mission. 
        Be concise but thorough. Focus ONLY on your specific area of expertise.
        """
        
        print(f"  [ParallelCrew] {self.role_name} working...")
        response = llm.query(prompt, complexity="L2", domain=self.domain)
        
        # Guard against None response from failed LLM
        if not response:
            print(f"  [ParallelCrew] WARNING: {self.role_name} got no response from LLM!")
            response = f"[{self.role_name}] Could not generate perspective due to LLM unavailability."
        
        print(f"  [DEBUG] PerspectiveAgent({self.role_name}): response_len={len(response)}")
        
        # Return ONLY this agent's contribution — the reducer will merge
        return {"parallel_outputs": {self.role_name: response}}

# Define Node Factories for different perspectives

def researcher_perspective(state: AgentState):
    agent = PerspectiveAgent(
        role_name="Researcher",
        mission="Gather facts, documentation, and existing solutions. Verify claims and provide evidence-based insights.",
        domain="research"
    )
    return agent.run(state)

def critic_perspective(state: AgentState):
    agent = PerspectiveAgent(
        role_name="Critical Reviewer",
        mission="Identify potential flaws, biases, risks, and edge cases in the request or proposed ideas.",
        domain="legal"
    )
    return agent.run(state)

def brainstormer_perspective(state: AgentState):
    agent = PerspectiveAgent(
        role_name="Creative Brainstormer",
        mission="Think outside the box. Suggest innovative, multi-disciplinary, and high-impact ideas or variations.",
        domain="growth"
    )
    return agent.run(state)

def practical_perspective(state: AgentState):
    agent = PerspectiveAgent(
        role_name="Practical Implementer",
        mission="Evaluate feasibility, resource requirements, and step-by-step execution plans.",
        domain="advisor"
    )
    return agent.run(state)

def analyst_perspective(state: AgentState):
    agent = PerspectiveAgent(
        role_name="Comparative Analyst",
        mission="Compare the request against industry standards, competitors, or alternative approaches.",
        domain="bank"
    )
    return agent.run(state)
