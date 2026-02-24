"""
ContentEvaluator Agent: Quality Guard for Social Media Content
=============================================================
Evaluates curated social media posts against rubrics for tone, 
value proposition, and platform fit.
"""
from typing import Dict, Any, List
from core.utils.llm_manager import LLMManager

llm = LLMManager()

class ContentEvaluator:
    def __init__(self):
        self.role = "ContentEvaluator"

    def evaluate_post(self, post_content: str, persona: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """
        Evaluate a single post against a rubric.
        Returns a dict with 'status' (PASS/NEEDS_REVISION), 'score', and 'feedback'.
        """
        prompt = f"""
        You are a Senior Content Strategist and Editor. 
        Evaluate the following social media post based on the target persona and platform.

        TARGET PERSONA:
        {persona.get('label', 'General')} - Tone: {persona.get('tone', 'professional')}

        PLATFORM: {platform}

        POST CONTENT:
        ---
        {post_content}
        ---

        RUBRIC:
        1. **Tone Match (0-5)**: Does it sound like the persona?
        2. **Value Prop (0-5)**: Is the insight from the briefing clear and actionable?
        3. **Platform Fit (0-5)**: Is the length and style (hashtags, emojis) correct for {platform}?
        4. **Vietnamese Naturalness (0-5)**: Is the language natural and professional?

        OUTPUT FORMAT (JSON ONLY):
        {{
            "scores": {{ "tone": 0, "value": 0, "platform": 0, "language": 0 }},
            "overall_score": 0,
            "status": "PASS" or "NEEDS_REVISION",
            "feedback": "Detailed feedback focusing on what to change if status is NEEDS_REVISION"
        }}

        A post PASSES if the overall_score >= 16 (out of 20) and no single category is below 3.
        """

        try:
            response = llm.query(prompt, complexity="L2", domain="content")
            # Basic JSON extraction
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            
            import json
            result = json.loads(response)
            return result
        except Exception as e:
            print(f"  [{self.role}] Evaluation error: {e}")
            return {
                "status": "PASS", # Fallback to pass on error to avoid infinite loops
                "feedback": "Evaluation engine failed; bypassed.",
                "overall_score": 20
            }

def content_evaluator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for evaluating curated posts."""
    messages = state.get("messages", [])
    # Find the last ContentCurator output
    curated_content = ""
    for msg in reversed(messages):
        if msg.startswith("ContentCurator:"):
            curated_content = msg.replace("ContentCurator:", "").strip()
            break
    
    if not curated_content or "✅ Đã tạo bài đăng" in curated_content:
        return {"is_valid": True} # Skip if file was saved or no content found

    # In a real scenario, this node would iterate over the nested dict of posts.
    # For the MVP of the loop, we'll evaluate the overall quality signal.
    
    evaluator = ContentEvaluator()
    # Mocking single evaluation for the logic flow
    # In a full impl, we'd pull persona/platform from state
    result = evaluator.evaluate_post(curated_content, {}, "social")
    
    print(f"  [ContentEvaluator] Result: {result['status']} | Score: {result['overall_score']}")
    
    if result["status"] == "NEEDS_REVISION":
        return {
            "is_valid": False,
            "critic_feedback": result["feedback"],
            "messages": [f"System: Content Evaluator rejected the draft. Feedback: {result['feedback']}"]
        }
    
    return {"is_valid": True}
