import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.utils.llm_manager import LLMManager

class MimiSynthesisAgent:
    """
    Agent responsible for analyzing Mimi's interaction logs,
    summarizing progress, identifying weaknesses, and generating
    pedagogical insights for parents.
    """
    def __init__(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.db_path = os.path.join(root_dir, "data", "mimi_interactions.db")
        self.llm = LLMManager()

    def get_recent_interactions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Fetch interactions from the last N hours."""
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        cursor.execute("SELECT * FROM interactions WHERE timestamp > ? ORDER BY timestamp ASC", (since,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def synthesize_session_report(self, interactions: List[Dict[str, Any]]) -> str:
        """Generates a structured insight report from a list of interactions."""
        if not interactions:
            return "Không có dữ liệu tương tác mới để tổng hợp."

        # Prepare context for LLM
        history_str = ""
        for i in interactions:
            history_str += f"- [{i['timestamp']}] Mimi: {i['user_input']}\n"
            history_str += f"  Assistant ({i['intent']}): {i['agent_output']}\n"

        prompt = f"""
        You are the Chief Pedagogical Officer. 
        Analyze the following interaction history between Mimi (student) and her AI Tutors.
        
        HISTORY:
        {history_str}
        
        MISSION:
        1. Summarize the main topics covered.
        2. Identify 'Knowledge Gaps' (questions Mimi struggled with).
        3. Rate Mimi's engagement level (high/medium/low).
        4. Suggest the next focus area for tomorrow.
        
        Format the report in VIETNAMESE as a markdown briefing for parents.
        """
        
        print(f"  [MimiSynthesis] Analyzing {len(interactions)} interactions...")
        return self.llm.query(prompt, complexity="L3")

def mimi_synthesis_node(state: Dict[str, Any]):
    """LangGraph node for recursive summarization."""
    agent = MimiSynthesisAgent()
    interactions = agent.get_recent_interactions(hours=state.get("synthesis_hours", 24))
    report = agent.synthesize_session_report(interactions)
    return {"messages": [f"System: Mimi Session Synthesis:\n{report}"]}

if __name__ == "__main__":
    agent = MimiSynthesisAgent()
    logs = agent.get_recent_interactions(hours=48)
    print(agent.synthesize_session_report(logs))
