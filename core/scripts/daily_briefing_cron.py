import asyncio
import os
import sys
from datetime import datetime

# Add root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(root_dir)

from core.agents.supervisor import build_supervisor_graph

async def run_daily_briefing():
    """
    Runs a proactive workflow to generate a daily briefing for the user.
    Can be scheduled via Crontab or PM2.
    """
    print(f"--- Starting Proactive Daily Briefing at {datetime.now()} ---")
    
    graph = build_supervisor_graph()
    
    # Simulate a user request for a daily briefing
    initial_state = {
        "messages": ["System: Generate my daily briefing. Summarize emails, schedule, and news."],
        "user_id": "default_user",
        "routing_category": "synthesis", # Direct to synthesis for deep aggregation
        "retry_count": 0,
        "is_valid": True
    }
    
    try:
        final_state = await graph.ainvoke(initial_state)
        briefing = final_state.get("messages", [])[-1]
        
        # In a real app, this would send a Telegram message or Email
        print("\n=== DAILY BRIEFING GENERATED ===")
        print(briefing)
        
        # Save to logs/briefings
        log_dir = os.path.join(root_dir, "logs", "briefings")
        os.makedirs(log_dir, exist_ok=True)
        filename = f"briefing_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(briefing)
            
        print(f"--- Briefing saved to {filename} ---")
        
    except Exception as e:
        print(f"Error generating briefing: {e}")

if __name__ == "__main__":
    asyncio.run(run_daily_briefing())
