import os
from core.state import AgentState
from core.document_loader import DocumentLoader
from core.vector_store_chroma import ChromaSkillStore
from core.utils.z_research import ZResearch
from core.mock_llm import MockLLM 

class KnowledgeAgent:
    def __init__(self):
        # Anchor to the actual project root (Orchesta assistant)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # For Orchesta assistant/05_Mimi_HomeTutor/core/agents/policy_agent.py, we need 3 levels up to hit Orchesta assistant
        project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
        
        # Mimi learning is a sibling to the Orchesta assistant folder
        self.mimi_learning_path = os.path.abspath(os.path.join(project_root, "../Mimi learning"))
        
        print(f"  [KnowledgeAgent] Init - current_dir: {current_dir}")
        print(f"  [KnowledgeAgent] Init - project_root: {project_root}")
        print(f"  [KnowledgeAgent] Init - mimi_learning_path: {self.mimi_learning_path} (Exists: {os.path.exists(self.mimi_learning_path)})")
        
        self.modules = [
            os.path.join(project_root, m) for m in [
                "01_Academic_Success",
                "02_Research_Scholarship",
                "03_Strategic_Advisory",
                "04_Banking_Support",
                "05_Mimi_HomeTutor",
                "06_Gamification_Tech",
                "07_Han_Media_Legal",
                "08_Growth_Branding",
                "09_Heritage_Scholar",
                "10_Wellness_Health",
                "11_Personal_Learning",
                "12_Executive_Ops"
            ]
        ]
        self.target_science_pdf = "pdfcoffee.com_mary-jones-cambridge-lower-secondary-science-7-learnerx27s-book-second-edition-pdf-free.pdf"
        self.modules.append(self.mimi_learning_path)
        self.loaders = [DocumentLoader(knowledge_base_path=m) for m in self.modules]
        self.store = ChromaSkillStore(persist_directory="chroma_knowledgedb")
        self.llm = MockLLM()
        self.researcher = ZResearch()

    def sync_manual_research(self):
        """
        Manually trigger ingestion of the research_results folder.
        """
        print("--- Đang đồng bộ kết quả nghiên cứu thủ công ---")
        loader = DocumentLoader(knowledge_base_path="research_results")
        docs = loader.load_documents()
        count = 0
        for doc in docs:
            doc_card = {
                "title": f"Manual Research: {doc['filename']}",
                "description": "Information manually collected from chat.z.ai",
                "logic_summary": doc["content"],
                "dependencies": [],
                "source_file": doc["filename"]
            }
            self.store.add_skill(doc_card)
            count += 1
        return count

    def sync_mimi_learning(self):
        """
        Ingests Mimi Science materials including PDFs and Markdown briefings.
        Supports both external paths and local 'materials' folder.
        """
        path = self.mimi_learning_path
        
        # Cloud Check: More robust pathing
        if not os.path.exists(path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.abspath(os.path.join(current_dir, "../../"))
            alt_path = os.path.join(backend_root, "materials")
            
            if os.path.exists(alt_path):
                path = alt_path
            else:
                os.makedirs(alt_path, exist_ok=True)
                return 0

        print(f"--- Đang đồng bộ tài liệu Science từ: {path} ---")
        
        # 1. Clear existing Mimi entries from store
        if hasattr(self.store, 'skills'):
            keys_to_delete = [k for k in self.store.skills.keys() if k.startswith("mimi_") or "science" in k]
            for k in keys_to_delete:
                del self.store.skills[k]
            print(f"  [KnowledgeAgent] Cleared {len(keys_to_delete)} existing Science entries.")

        # 2. Load documents
        loader = DocumentLoader(knowledge_base_path=path)
        docs = loader.load_documents()
        
        count = 0
        for doc in docs:
            # Skip files with empty content (common for image-only PDFs)
            if not doc['content'] or len(doc['content'].strip()) < 10:
                print(f"  [KnowledgeAgent] Skipping empty file: {doc['filename']}")
                continue

            # Identify if it's the primary Stage 7 textbook or a briefing
            title = f"Mimi Science: {doc['filename']}"
            desc = "Science Stage 7 Study Material."
            
            if "Briefing" in doc['filename']:
                desc = "Technical curriculum summary for a specific unit."
            elif "Adventure" in doc['filename']:
                desc = "Friendly, story-based explanation for Mimi."
            
            doc_card = {
                "title": title,
                "description": desc,
                "logic_summary": doc["content"],
                "dependencies": [],
                "source_file": doc["filename"]
            }
            self.store.add_skill(doc_card)
            count += 1
        
        print(f"  [KnowledgeAgent] Successfully ingested {count} Science materials.")
        return count

    def answer_question(self, question: str, role_category: str = "academic", memory: list = None, feedback: str = None) -> str:
        """
        Retrieves docs and answers using the specific agent's role prompt and long-term memory.
        """
        # ... (mapping same)
        prompt_map = {
            "research": "research_scholarship_lead",
            "bank": "shadow_bank_consultant",
            "tech": "creative_tech_skill_architect",
            "growth": "growth_branding_specialist",
            "academic": "academic_success_assistant",
            "advisor": "strategic_advisory_consultant",
            "legal": "han_media_legal_guardian",
            "mimi": "mimi_socratic",
            "cos": "executive_chief_of_staff",
            "heritage": "heritage_philosophy_scholar",
            "wellness": "wellness_performance_coach",
            "learning": "personal_intellectual_tutor"
        }
        
        system_prompt = ""
        filename = prompt_map.get(role_category, "academic_student_success")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "../../prompts", f"{filename}.md")
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        except:
            print(f"Warning: Could not find prompt for {role_category} at {prompt_path}")

        results = self.store.search_skills(question)
        context = ""
        if results:
            context = "\n".join([f"Source ({r['title']}): {r['logic_summary'][:1000]}" for r in results])
        
        memory_str = "\n".join([f"- {m}" for m in memory]) if memory else "None."
        
        feedback_section = f"\n--- CRITIC FEEDBACK (REVISE YOUR PREVIOUS RESPONSE) ---\n{feedback}\n" if feedback else ""

        full_prompt = f"""
        {system_prompt}
        {feedback_section}
        
        --- LONG-TERM MEMORY (USER PROFILE) ---
        {memory_str}

        --- CONTEXT FROM KNOWLEDGE BASE ---
        {context if context else 'No local document found.'}
        
        USER QUESTION: {question}
        """
        print(f"  [GLM-5] Generating specialized answer as {role_category} (with memory context)...")
        answer = self.researcher.query(full_prompt)
        
        if answer == "FALLBACK_TRIGGERED":
            return f"Anh/Chị Lead {role_category.capitalize()} đây! Hiện tại bộ não của anh/chị đang bảo trì, bù lại anh/chị có thông tin này: {context[:500] if context else 'Hãy thử hỏi câu khác cụ thể hơn nhé!'}"
        
        return answer

def knowledge_agent_node(state: AgentState):
    agent = KnowledgeAgent()
    if state["messages"]:
        question = state["messages"][-1]
        category = state.get("routing_category", "academic")
        memory = state.get("long_term_memory", [])
        feedback = state.get("critic_feedback")
        answer = agent.answer_question(question, role_category=category, memory=memory, feedback=feedback)
        return {"messages": [f"{category.capitalize()} Lead: {answer}"]}
    return {"messages": ["Knowledge Agent: No question found."]}

if __name__ == "__main__":
    agent = KnowledgeAgent()
    print("--- Thử nghiệm đồng bộ kết quả nghiên cứu thủ công ---")
    count = agent.sync_manual_research()
    print(f"Đã nạp {count} tài liệu nghiên cứu mới.")
    
    question = "Hệ thống đa đại lý là gì?"
    print(f"\n--- Đang trả lời câu hỏi: {question} ---")
    answer = agent.answer_question(question)
    print(answer)
