import asyncio
import json
import os
from core.utils.z_research import ZResearch

# Topics to research
RESEARCH_TOPICS = {
    "Educational_Chatbot_Architectures": "Nghiên cứu kiến trúc chatbot giáo dục hiện đại. Tập trung vào thiết kế agent đa tầng (multi-layer), mô hình supervisor-worker trong giáo dục (như LangGraph, AutoGen). Ưu điểm và nhược điểm của từng loại.",
    "Multi_Agent_Systems_for_Tutoring": "Nghiên cứu hệ thống đa tác vụ (Multi-Agent Systems - MAS) áp dụng cho gia sư (tutoring). Các vai trò chuyên biệt như Expert, Pedagogy Expert, Motivator làm việc cùng nhau như thế nào để cá nhân hóa việc học?",
    "Socratic_Tutoring_Prompting": "Kỹ thuật Prompting cho phương pháp học Socratic (Socratic Tutoring). Làm thế nào để khuyến khích tư duy phản biện qua chatbot, phương pháp 'scaffolding' và gợi mở thay vì đưa đáp án trực tiếp?",
    "Technical_Integration_NotebookLM_Colab": "Nghiên cứu cách tích hợp NotebookLM-style knowledge base với môi trường thực thi code (như Google Colab) trong một luồng làm việc agentic. Cách xử lý dữ liệu từ PDF/Excel vào LLM hiệu quả.",
    "Gamification_Strategies_Learner_Engagement": "Các chiến lược Gamification (game hóa) hiệu quả nhất cho người học chuyên nghiệp và học sinh K-12 trong giao diện chatbot. Phần thưởng, theo dõi tiến độ, và yếu tố kể chuyện (narrative)."
}

async def run_query(researcher, topic_id, prompt):
    print(f"Starting research for: {topic_id}...")
    # Wrap researcher.query in a thread since it's synchronous
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, researcher.query, prompt)
    print(f"Finished research for: {topic_id}.")
    return topic_id, result

async def main():
    researcher = ZResearch()
    tasks = []
    
    for topic_id, prompt in RESEARCH_TOPICS.items():
        tasks.append(run_query(researcher, topic_id, prompt))
    
    results = await asyncio.gather(*tasks)
    
    output_temp = {topic_id: content for topic_id, content in results}
    
    output_path = "research_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_temp, f, ensure_ascii=False, indent=4)
    
    print(f"All research completed. Results saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
