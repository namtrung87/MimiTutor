import os
from core.state import AgentState
from core.document_loader import DocumentLoader
from core.vector_store_chroma import ChromaSkillStore
from core.utils.z_research import ZResearch
from core.mock_llm import MockLLM 

class KnowledgeAgent:
    def __init__(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.modules = [
            os.path.join(root_dir, m) for m in [
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
        # Special handling for Mimi learning which is outside the assistant folder
        self.mimi_learning_path = os.path.abspath(os.path.join(root_dir, "../Mimi learning"))
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
        Ingests ONLY the specific Mimi Science textbook.
        Clears existing Mimi entries first to ensure Science-only focus.
        """
        path = self.mimi_learning_path
        target_file = self.target_science_pdf
        
        print(f"--- Đang đồng bộ tài liệu Science cho Mimi từ: {target_file} ---")
        
        # 1. Clear existing Mimi entries from store
        if hasattr(self.store, 'skills'):
            # Match actual keys which look like 'mimi_learning:...'
            keys_to_delete = [k for k in self.store.skills.keys() if k.startswith("mimi_learning:")]
            for k in keys_to_delete:
                del self.store.skills[k]
            print(f"  [KnowledgeAgent] Cleared {len(keys_to_delete)} existing Mimi entries.")

        # 2. Load only the target PDF
        loader = DocumentLoader(knowledge_base_path=path)
        docs = loader.load_documents()
        
        count = 0
        for doc in docs:
            if doc['filename'] == target_file:
                doc_card = {
                    "title": f"Mimi Science: {doc['filename']}",
                    "description": "Cambridge Lower Secondary Science 7 Learner's Book.",
                    "logic_summary": doc["content"],
                    "dependencies": [],
                    "source_file": doc["filename"]
                }
                self.store.add_skill(doc_card)
                count += 1
                break
        
        if count == 0:
            print(f"  [WARNING] Target Science PDF not found: {target_file}")
        else:
            print(f"  [KnowledgeAgent] Successfully ingested Science material.")
            
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
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        prompt_path = os.path.join(root_dir, "prompts", f"{filename}.md")
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
