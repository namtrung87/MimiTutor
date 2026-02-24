from core.utils.z_research import ZResearch
import json

RESEARCH_TOPICS = [
    "Educational Chatbot Architectures (Multi-layer, Supervisor-Worker, LangGraph, AutoGen)",
    "Multi-Agent Systems for Tutoring (Content Expert, Pedagogy Expert, Motivator)",
    "Socratic Tutoring & Prompt Engineering (Scaffolding, Critical Thinking)",
    "Technical Integration (NotebookLM, Google Colab, GLM, PDF/Excel Processing)",
    "Gamification Strategies for Learner Engagement (Narrative, Rewards, Progress Tracking)"
]

def main():
    researcher = ZResearch()
    all_strategies = []
    
    print("# 📋 DANH SÁCH PROMPT NGHIÊN CỨU CHO Z.AI\n")
    print("Vui lòng copy từng prompt dưới đây vào [chat.z.ai](https://chat.z.ai), sau đó lưu kết quả vào thư mục `research_results/`.\n")
    
    for topic in RESEARCH_TOPICS:
        strategy = researcher.generate_research_strategy(topic)
        print(f"## 🔍 Chủ đề: {topic}")
        print(f"**Các tiểu mục gợi ý:**")
        for st in strategy['sub_topics']:
            print(f"- {st}")
        print(f"\n**Prompt để Copy-Paste:**")
        print("```text")
        print(strategy['copy_paste_prompt'])
        print("```")
        print("\n---\n")

if __name__ == "__main__":
    main()
