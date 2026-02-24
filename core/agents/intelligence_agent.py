from core.state import AgentState
from core.utils.llm_manager import LLMManager
from typing import Dict, Any

llm = LLMManager()

class IntelligenceAgent:
    """
    Agent responsible for processing AI news, library updates, and workflow tips.
    It categorizes raw data and formats it for team consumption.
    """
    def __init__(self):
        self.role = "AI Intelligence Officer"
        self.mission = (
            "Analyze raw AI news, GitHub updates, and research papers. "
            "Categorize them into 'Technical', 'Workflow', or 'Prompting Tips'. "
            "Synthesize actionable insights for the AI agent team."
        )

    def process_intelligence(self, raw_input: str) -> Dict[str, Any]:
        """
        Takes raw news data and produces a structured summary.
        """
        prompt = f"""
        You are the {self.role}. 
        MISSION: {self.mission}
        
        RAW NEWS DATA:
        {raw_input}
        
        TASK:
        1. Identify the top 3-5 most impactful updates.
        2. For each update, provide:
           - Title
           - Category (Technical / Workflow / Tip)
           - Impact Score (1-10)
           - Actionable Insight: How can our team of AI agents use this?
        3. Provide a 'Chốt lại' (final summary) in Vietnamese.
        
        Format the output clearly for a Telegram message.
        """
        
        print(f"  [{self.role}] Analyzing latest AI trends...")
        summary = llm.query(prompt, complexity="L3", domain="research")
        
        return {
            "intelligence_report": summary,
            "messages": [f"Intelligence Report generated: {summary[:100]}..."]
        }

def intelligence_node(state: AgentState):
    """
    Node for LangGraph integration.
    Expects raw news in state['raw_news'].
    """
    agent = IntelligenceAgent()
    raw_news = state.get("raw_news", "No new data found today.")
    result = agent.process_intelligence(raw_news)
    
    # Update state with the report
    return {"messages": [result["intelligence_report"]]}
