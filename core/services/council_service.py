import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from core.utils.llm_manager import LLMManager
from core.utils.bot_logger import get_logger

logger = get_logger("council_service")

class CouncilService:
    """
    Manages a collective of LLMs to solve high-complexity problems.
    Logic:
    1. Parallel Queries: Ask N models the same question.
    2. Synthesis: A "Chairman" model reviews all answers and provides the final best response.
    """
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        self.llm = llm_manager or LLMManager()
        self.config_path = os.path.join(os.path.dirname(__file__), "../utils/council_config.json")
        self.config = self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "councils": {
                "elite": [
                    "anthropic/claude-3.5-sonnet",
                    "openai/gpt-4o",
                    "google/gemini-1.5-pro"
                ],
                "fast": [
                    "groq/llama-3.3-70b-versatile",
                    "gemini/gemini-1.5-flash-latest",
                    "mistral/pixtral-12b"
                ]
            },
            "default_chairman": "gemini/gemini-2.0-flash-thinking-exp"
        }

    async def deliberate(self, query: str, council_tier: str = "elite") -> str:
        """
        Runs the council deliberation process.
        """
        models = self.config["councils"].get(council_tier, self.config["councils"]["fast"])
        logger.info(f"Council deliberation started with {len(models)} models ({council_tier} tier).")
        
        # Parallel Queries
        prompts = [query] * len(models)
        results = await self.llm.batch_query(prompts, models)
        
        # Filter out failed responses
        valid_responses = []
        for i, res in enumerate(results):
            if res:
                valid_responses.append(f"--- Model: {models[i]} ---\n{res}")
        
        if not valid_responses:
            return "Council deliberation failed: No valid responses from any model."

        # Synthesis
        chairman_model = self.config.get("default_chairman", "gemini-2.0-flash")
        synthesis_prompt = f"""
        You are the Chairman of the LLM Council. 
        The user has asked the following question:
        "{query}"

        Below are the perspectives from {len(valid_responses)} different high-end models:

        {"\n\n".join(valid_responses)}

        MISSION:
        1. Critically evaluate all perspectives.
        2. Identify consensus points and unique insights.
        3. Resolve any contradictions.
        4. Synthesize a single, definitive, and high-quality response for the user.
        
        Format your final answer professionally. Highlight which models provided key insights if relevant.
        """
        
        logger.info(f"Chairman ({chairman_model}) is synthesizing final response...")
        final_answer = await self.llm.query(synthesis_prompt, complexity="L3", model_override=chairman_model)
        
        return final_answer or "Synthesis failed. Please review raw logs."

if __name__ == "__main__":
    async def test():
        service = CouncilService()
        res = await service.deliberate("What is the best strategy for local SEO for a Vietnamese coffee shop in 2026?", council_tier="fast")
        print("\n--- COUNCIL RESULT ---\n")
        print(res)

    asyncio.run(test())
