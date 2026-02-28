import asyncio
from typing import Dict, Any, List, Optional
from core.utils.bot_logger import get_logger
from core.llm import LLMManager
from core.services.notification_batcher import notification_batcher

logger = get_logger("content_pipeline")

class ContentPipeline:
    """
    Orchestrates complex multi-agent workflows for content generation.
    Sequence: Research -> Draft -> Critic -> Batch/Publish.
    """
    def __init__(self):
        self.llm = LLMManager(app_name="content_pipeline")

    async def run_pipeline(self, topic: str, target_audience: str = "general") -> Dict[str, Any]:
        """
        Runs the full content generation pipeline.
        """
        logger.info(f"Starting content pipeline for topic: {topic}")
        
        # 1. Research Phase
        research_data = await self._research_phase(topic)
        
        # 2. Drafting Phase
        draft = await self._drafting_phase(topic, research_data, target_audience)
        
        # 3. Criticism/Review Phase
        final_content = await self._critic_phase(draft)
        
        # 4. Delivery Phase
        notification_batcher.add_notification(
            f"🚀 **New Content Generated**\n\nTopic: {topic}\n\n{final_content}",
            category="content_pipeline"
        )
        
        return {
            "topic": topic,
            "status": "published",
            "content_length": len(final_content)
        }

    async def _research_phase(self, topic: str) -> str:
        logger.info("  [Pipeline] Phase 1: Deep Research...")
        prompt = f"Conduct deep research on the following topic and provide key technical insights: {topic}"
        # Simulate agent call
        return self.llm.query(prompt, complexity="L3", domain="research")

    async def _drafting_phase(self, topic: str, research: str, audience: str) -> str:
        logger.info("  [Pipeline] Phase 2: Content Drafting...")
        prompt = f"""
        Topic: {topic}
        Research Data: {research}
        Audience: {audience}
        
        Draft a high-quality article or social media post based on the research data.
        """
        return self.llm.query(prompt, complexity="L2", domain="growth")

    async def _critic_phase(self, draft: str) -> str:
        logger.info("  [Pipeline] Phase 3: Expert Review...")
        prompt = f"""
        Review and enhance the following draft for clarity, engagement, and accuracy:
        
        DRAFT:
        {draft}
        
        Provide only the finalized, improved version of the text.
        """
        return self.llm.query(prompt, complexity="L3", domain="critic")

content_pipeline = ContentPipeline()
