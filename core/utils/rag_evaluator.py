from core.utils.llm_manager import LLMManager
from typing import List, Dict, Any

class RAGEvaluator:
    """
    Uses Ragas principles to evaluate RAG quality.
    Focuses on Faithfulness and Answer Relevance.
    """
    def __init__(self):
        self.llm = LLMManager()

    def evaluate(self, question: str, context: str, answer: str) -> Dict[str, Any]:
        """
        Evaluates a single RAG triplet.
        """
        print(f"  [Ragas] Evaluating faithfulness and relevance...")
        
        # 1. Faithfulness (Is the answer derived from context?)
        faith_prompt = f"""
        Given the following CONTEXT and ANSWER, can the answer be inferred ENTIRELY from the context?
        CONTEXT: {context}
        ANSWER: {answer}
        Respond with a score 0-10 and a brief reason.
        """
        faith_res = self.llm.query(faith_prompt, complexity="L2", domain="reasoning")
        
        # 2. Answer Relevance (Does the answer address the question?)
        relevance_prompt = f"""
        Given the QUESTION and the ANSWER, how relevant is the answer to the question?
        QUESTION: {question}
        ANSWER: {answer}
        Respond with a score 0-10 and a brief reason.
        """
        rel_res = self.llm.query(relevance_prompt, complexity="L2", domain="reasoning")
        
        return {
            "faithfulness": faith_res,
            "relevance": rel_res
        }
