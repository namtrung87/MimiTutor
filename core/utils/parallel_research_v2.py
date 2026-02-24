import concurrent.futures
import json
import os
import sys
from datetime import datetime

# Add the parent directory to sys.path to import ZResearch
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from core.utils.z_research import ZResearch

def run_cert_agent(agent_name, cert_name, extra_prompt):
    print(f"[*] Agent '{agent_name}' researching {cert_name} (Broad Scope)...")
    researcher = ZResearch()
    
    prompt = f"""As a professional education researcher, identify the top 'pain point' topics for learners across the ENTIRE syllabus of the {cert_name} certification. 
    Do not focus on just one level or a few subjects; provide a comprehensive overview of the most difficult concepts throughout the whole curriculum.
    
    For each major stage or category of the certification, identify the specific topic-level 'pain point' (e.g., 'Absorption Costing', 'Deferred Tax', 'Options Greeks', 'Consolidation', 'Audit Risk Assessment').
    
    For each identified topic, provide:
    1. Topic Name and Subject/Level it belongs to.
    2. Why it is difficult (the specific 'pain point' for learners).
    3. A brief suggestion for a gamified mechanic to solve it.
    
    Format the response clearly with headings and bullet points. Ensure high-quality, actionable insights."""

    try:
        result = researcher.query(prompt)
        print(f"[+] Agent '{agent_name}' ({cert_name}) completed.")
        return {
            "agent": agent_name,
            "certification": cert_name,
            "timestamp": datetime.now().isoformat(),
            "content": result
        }
    except Exception as e:
        print(f"[-] Agent '{agent_name}' ({cert_name}) failed: {str(e)}")
        return {
            "agent": agent_name,
            "certification": cert_name,
            "error": str(e)
        }

def main():
    agents = [
        {"name": "Agent 1", "cert": "CFA (Chartered Financial Analyst)"},
        {"name": "Agent 2", "cert": "ACCA (Association of Chartered Certified Accountants)"},
        {"name": "Agent 3", "cert": "ICAEW (ACA)"},
        {"name": "Agent 4", "cert": "CIMA (CGMA - Chartered Global Management Accountant)"},
        {"name": "Agent 5", "cert": "CPA Australia"}
    ]

    print(f"--- Starting Parallel Certification Research (Broad Scope) with 5 GLM-5 Agents ---")
    results = []
    
    # We use ThreadPoolExecutor. ZResearch handles the 5-concurrency limit via its internal semaphore.
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as executor:
        futures = [executor.submit(run_cert_agent, a["name"], a["cert"], "") for a in agents]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    output_path = "certification_pain_points_broad.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"--- Research Completed. Results saved to {output_path} ---")

if __name__ == "__main__":
    main()
