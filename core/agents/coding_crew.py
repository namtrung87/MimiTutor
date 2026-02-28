from core.state import AgentState
from core.utils.llm_manager import LLMManager
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:
    # Minimal fallback models for CrewAI-like behavior if install fails
    class Agent:
        def __init__(self, **kwargs): self.data = kwargs
    class Task:
        def __init__(self, **kwargs): self.data = kwargs
    class Crew:
        def __init__(self, **kwargs): self.data = kwargs
        def kickoff(self): return "CrewAI not installed. Falling back to sequential."

import json
import os

llm_manager = LLMManager()

def _load_prompt(filename):
    root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../.."))
    prompt_path = os.path.join(root_dir, "prompts", filename)
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    return f"You are a coding professional specialized in {filename}."

class CodingCrewManager:
    """Manages the CrewAI team for coding tasks."""
    
    @staticmethod
    def get_crew(user_input: str, context: str = ""):
        # 1. Define Agents
        researcher = Agent(
            role='Senior Research Engineer',
            goal='Find the best libraries and documentation for: {input}',
            backstory='Expert at technical documentation and identifying modern best practices.',
            allow_delegation=False,
            verbose=True
        )

        developer = Agent(
            role='Senior Python Developer',
            goal='Implement a robust, clean solution for: {input}.',
            backstory='A veteran engineer who writes clean, tested, and high-performance code.',
            allow_delegation=True,
            verbose=True
        )

        tester = Agent(
            role='QA Engineer',
            goal='Write comprehensive unit tests (using pytest) for the code produced by the developer.',
            backstory='You believe that code without tests is broken. You ensure 100% logic coverage.',
            allow_delegation=False,
            verbose=True
        )

        executor = Agent(
            role='Execution Sandbox',
            goal='Run the provided tests and code in a safe environment. Report any Tracebacks or assertion failures.',
            backstory='You are a terminal-focused specialist. You provide raw log output and exit codes.',
            allow_delegation=False,
            verbose=True
        )

        auditor = Agent(
            role='Security & Quality Auditor',
            goal='Final review. Check code quality, security, and test results.',
            backstory='The final gatekeeper. You only approve code that is secure, efficient, and passes all tests.',
            allow_delegation=False,
            verbose=True
        )

        # 2. Define Tasks
        task_research = Task(
            description=f"Research technical requirements for: {user_input}. Context: {context}",
            agent=researcher,
            expected_output="A summary of tools, libraries, and logic steps."
        )

        task_dev = Task(
            description=f"Develop the implementation. User Request: {user_input}",
            agent=developer,
            context=[task_research],
            expected_output="Complete Python code block."
        )

        task_test = Task(
            description="Write a Python script containing unit tests for the developer's code.",
            agent=tester,
            context=[task_dev],
            expected_output="A Python script with pytest-compliant tests."
        )

        task_exec = Task(
            description="Execute the developer's code and tests in a virtual sandbox. Report any errors.",
            agent=executor,
            context=[task_dev, task_test],
            expected_output="Terminal output from the execution."
        )

        task_audit = Task(
            description="Audit the provided code and test results. Output MUST be valid JSON with 'is_valid' and 'feedback' keys.",
            agent=auditor,
            context=[task_dev, task_test, task_exec],
            expected_output="JSON audit report including 'is_valid' (boolean) and 'feedback' (string)."
        )

        # 3. Create Crew
        return Crew(
            agents=[researcher, developer, tester, executor, auditor],
            tasks=[task_research, task_dev, task_test, task_exec, task_audit],
            process=Process.sequential,
            verbose=True
        )

def coding_crew_node(state: AgentState):
    """
    Unified LangGraph node that kicks off the CrewAI process with self-healing.
    """
    user_input = state.messages[-1]
    memory = state.long_term_memory or []
    
    print(f"  [CodingCrew] 🚀 Kicking off Autonomous Team for: {user_input[:50]}...")
    
    crew_manager = CodingCrewManager()
    crew = crew_manager.get_crew(user_input, context=str(memory))
    
    result = crew.kickoff()
    result_str = str(result)
    
    # Try to extract JSON from the final auditor output
    is_valid = True
    try:
        # Simple extraction if result contains JSON
        if "{" in result_str:
            start = result_str.find("{")
            end = result_str.rfind("}") + 1
            json_str = result_str[start:end]
            data = json.loads(json_str)
            is_valid = data.get("is_valid", True)
    except Exception as e:
        print(f"  [CodingCrew] Audit parse error: {e}")

    return {
        "messages": [f"Coding Crew: {result_str}"],
        "is_valid": is_valid
    }

# Keeping legacy node stubs for backward compatibility in the graph if needed
def developer_node(state: AgentState): return coding_crew_node(state)
def auditor_node(state: AgentState): return {"is_valid": True}
def researcher_node(state: AgentState): return {"research_output": "Done via Crew."}
def synthesis_node(state: AgentState): return {"messages": ["Synthesis handled by Crew."]}
