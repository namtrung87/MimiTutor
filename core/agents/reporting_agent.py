import os
import json
from core.utils.z_research import ZResearch
from datetime import datetime

class ReportingAgent:
    """
    Analyzes Mimi's chat logs to generate reports for parents.
    """
    def __init__(self, log_dir="04_Personal_Development/Home_Tutor/chat_history"):
        self.log_dir = log_dir
        self.researcher = ZResearch()

    def generate_report(self, date_str=None):
        """
        Generates a summary report for a specific date (YYYYMMDD).
        If no date is provided, it summarizes the most recent log.
        """
        if not os.path.exists(self.log_dir):
            return "No chat history found."

        if date_str:
            log_file = os.path.join(self.log_dir, f"session_{date_str}.jsonl")
        else:
            # Get the most recent log file
            files = [f for f in os.listdir(self.log_dir) if f.startswith("session_") and f.endswith(".jsonl")]
            if not files:
                return "No chat logs available."
            log_file = os.path.join(self.log_dir, sorted(files)[-1])

        if not os.path.exists(log_file):
            return f"No log file found for {date_str or 'recent session'}."

        with open(log_file, 'r', encoding='utf-8') as f:
            logs = [json.loads(line) for line in f]

        # Prepare logs for AI analysis
        log_summary = "\n".join([f"[{l['timestamp']}] Student: {l['user']} | Tutor: {l['bot']}" for l in logs])

        prompt = f"""
        Analyze the following chat logs between Mimi (Student) and her Socratic Tutor.
        
        LOGS:
        {log_summary}
        
        TASK: Generate a report for the parent (in Vietnamese) covering:
        1. **Summary of Topics**: What did Mimi learn or practice today?
        2. **Engagement & Behavior**: Did she show signs of laziness, frustration, or great focus?
        3. **Sticking Points**: What concepts did she struggle with the most?
        4. **Improvement Plan**: Specific steps or topics to focus on tomorrow to help her improve.
        
        TONE: Professional yet encouraging.
        """
        
        report = self.researcher.query(prompt)
        return report

def reporting_agent_node(state):
    # This node could be triggered by a specific "Parent" request
    agent = ReportingAgent()
    report = agent.generate_report()
    return {"messages": [f"Parent Report:\n{report}"]}
