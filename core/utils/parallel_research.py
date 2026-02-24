import concurrent.futures
import json
import os
import sys
from datetime import datetime

# Add the parent directory to sys.path to import ZResearch
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from core.utils.z_research import ZResearch

def run_agent_task(agent_name, prompt):
    print(f"[*] Agent '{agent_name}' starting research...")
    researcher = ZResearch()
    try:
        result = researcher.query(prompt)
        print(f"[+] Agent '{agent_name}' completed.")
        return {
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "content": result
        }
    except Exception as e:
        print(f"[-] Agent '{agent_name}' failed: {str(e)}")
        return {
            "agent": agent_name,
            "error": str(e)
        }

def main():
    tasks = {
        "Psychology Agent": "Identify psychological barriers in learning (lack of motivation, burnout, cognitive load). How can gamification address these? Provide 3 specific pain points and 3 gamified solutions.",
        "Structure Agent": "Research organizational pain points in curriculum design (information overload, lack of clear path). Provide 3 specific pain points and 3 gamified solutions.",
        "Community Agent": "Research social pain points in learning (isolation, lack of feedback). Provide 3 specific pain points and 3 gamified solutions.",
        "Trend Agent": "Analyze successful gamification models (Duolingo, Khan Academy). What specific learner frustrations did they solve? Provide 3 examples.",
        "Demographic Agent": "Focused on student/professional pain points in 2024-2025 (distraction, need for ROI). Provide 3 specific pain points and 3 gamified solutions."
    }

    print(f"--- Starting Parallel Research with {len(tasks)} Agents ---")
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_agent = {executor.submit(run_agent_task, name, prompt): name for name, prompt in tasks.items()}
        for future in concurrent.futures.as_completed(future_to_agent):
            results.append(future.result())

    output_path = "research_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"--- Research Completed. Results saved to {output_path} ---")

if __name__ == "__main__":
    main()
