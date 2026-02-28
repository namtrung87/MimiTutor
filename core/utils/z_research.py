import os
import json
import requests
import threading
import glob
from dotenv import load_dotenv

load_dotenv()

class ZResearch:
    """
    Research Strategist & Coordinator: 
    - Generates optimized prompts for manual use on chat.z.ai.
    - Ingests manually collected results.
    - Provides internal LLM query capability for agent coordination (routing/extraction).
    """
    def __init__(self, results_folder="research_results"):
        from core.utils.llm_manager import LLMManager
        self.llm_manager = LLMManager()
        self.results_folder = results_folder
        if not os.path.exists(self.results_folder):
            os.makedirs(self.results_folder)

    def query(self, prompt: str, complexity: str = "auto", thinking_depth: str = "auto") -> str:
        """Internal API query via LLMManager fallback chain with Opus thinking."""
        return self.llm_manager.query_sync(prompt, complexity=complexity)

    def generate_research_strategy(self, query: str) -> dict:
        """Breaks down a query and provides a copy-paste prompt for chat.z.ai."""
        sub_topics = [f"Tổng quan: {query}", f"Chuyên sâu & Kỹ thuật: {query}", f"Xu hướng 2025: {query}"]
        main_prompt = f"Chào Z.ai, tôi cần một nghiên cứu chuyên sâu về: '{query}'. Vui lòng phân tích chi tiết các khía cạnh: tổng quan, nguyên lý, thách thức và xu hướng mới nhất."
        return {"query": query, "sub_topics": sub_topics, "copy_paste_prompt": main_prompt}

    def ingest_manual_results(self) -> str:
        """Consolidates files from search_results folder."""
        files = glob.glob(os.path.join(self.results_folder, "*.*"))
        content = [f"--- File: {os.path.basename(f)} ---\n{open(f, 'r', encoding='utf-8').read()}" for f in files]
        return "\n".join(content) if content else "Không tìm thấy dữ liệu."
