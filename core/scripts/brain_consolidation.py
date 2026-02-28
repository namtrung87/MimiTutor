import os
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT) # Ensure we run from root

from core.utils.llm_manager import LLMManager

def consolidate_brain():
    brain_path = "BRAIN.md"
    supervisor_prompt_path = "prompts/supervisor.md"
    
    if not os.path.exists(brain_path):
        print("BRAIN.md not found.")
        return

    with open(brain_path, "r", encoding="utf-8") as f:
        brain_content = f.read()

    # Extract REVISE sections
    revised_parts = [line for line in brain_content.split("\n") if "REVISE" in line or "hallucination" in line.lower()]
    
    if not revised_parts:
        print("No hallucinations or revisions found in BRAIN.md.")
        return

    print("Found friction in BRAIN.md. Analyzing...")

    llm = LLMManager()
    
    analysis_prompt = f"""
    Bạn là System Architect của Orchesta Assistant.
    Dưới đây là danh sách các lỗi (hallucinations, misrouting, poor tone) được ghi nhận trong BRAIN.md:
    
    {chr(10).join(revised_parts)}
    
    NHIỆM VỤ:
    Tạo ra một danh sách ngắn gọn các "NEGATIVE CONSTRAINTS" (những gì KHÔNG được làm) để bổ sung vào Supervisor Prompt nhằm tránh lặp lại các lỗi này.
    Focus vào: Tránh trả lời trực tiếp khi đóng vai Socratic (Mimi), tránh hallucinate token counts, tránh nhầm lẫn category.
    
    Trả về kết quả dưới dạng bullet points.
    """
    
    constraints = llm.query(analysis_prompt, complexity="L2")
    
    if os.path.exists(supervisor_prompt_path):
        with open(supervisor_prompt_path, "r", encoding="utf-8") as f:
            current_prompt = f.read()
        
        if "## 🛑 NEGATIVE CONSTRAINTS (Self-Healed)" in current_prompt:
             # Already exists, we might want to replace or update. For now, let's append safely.
             print("Negative constraints already exist. Skipping duplicate addition.")
             return

        updated_prompt = current_prompt + "\n\n## 🛑 NEGATIVE CONSTRAINTS (Self-Healed)\n" + constraints
        
        with open(supervisor_prompt_path, "w", encoding="utf-8") as f:
            f.write(updated_prompt)
        
        print("Successfully updated supervisor.md with anti-hallucination constraints.")
    else:
        print("supervisor.md prompt not found. Skill aborted.")

if __name__ == "__main__":
    consolidate_brain()
