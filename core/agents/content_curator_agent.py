"""
ContentCurator Agent: TrendScout Briefing → Social Media Posts
==============================================================
Transforms TrendScout daily intelligence reports into audience-targeted
social media content for personal branding.

Target Audiences:
  1. Finance Professionals (KT-KiT-TC practitioners)
  2. Finance Students (SV KT-KiT-TC)
  3. Educators (general education / EdTech)
  4. Finance Educators (GV dạy KT-KiT-TC)

Platforms: LinkedIn, Facebook, TikTok, Zalo OA, Telegram
"""
import os
import json
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.state import AgentState
from core.utils.llm_manager import LLMManager

llm = LLMManager()

# ─── Paths ─────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PERSONAS_PATH = os.path.join(BASE_DIR, "08_Growth_Branding", "audience_personas.json")
PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "content_curator_social.md")
BRIEFING_DIR = os.path.join(BASE_DIR, "11_Personal_Learning", "summaries")
CURATED_OUTPUT_DIR = os.path.join(BASE_DIR, "08_Growth_Branding", "curated")


class ContentCuratorAgent:
    """
    Agent that reads TrendScout briefings and produces
    audience-targeted social media posts for personal branding.
    """

    def __init__(self):
        self.role = "ContentCurator"
        self.personas: Dict[str, Any] = {}
        self.platform_config: Dict[str, Any] = {}
        self.prompt_template: str = ""
        self._load_resources()

    # ── Resource Loading ─────────────────────────────────────────

    def _load_resources(self):
        """Load audience personas and prompt template from disk."""
        self._load_personas()
        self.prompt_template = self._load_prompt_template()

    def _load_personas(self):
        """Load audience personas from JSON."""
        if not os.path.exists(PERSONAS_PATH):
            print(f"  [{self.role}] Warning: Personas not found at {PERSONAS_PATH}")
            return
        try:
            with open(PERSONAS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.personas = data.get("personas", {})
            self.platform_config = data.get("platform_config", {})
            print(f"  [{self.role}] Loaded {len(self.personas)} audience personas")
        except Exception as e:
            print(f"  [{self.role}] Error loading personas: {e}")

    def _load_prompt_template(self) -> str:
        """Load the curator prompt template from disk."""
        if not os.path.exists(PROMPT_PATH):
            print(f"  [{self.role}] Warning: Prompt template not found at {PROMPT_PATH}")
            return ""
        try:
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"  [{self.role}] Error loading prompt: {e}")
            return ""

    # ── Briefing Reading ─────────────────────────────────────────

    def get_latest_briefing(self) -> Optional[str]:
        """
        Read the most recent TrendScout briefing from disk.
        Returns the briefing text or None if not found.
        """
        if not os.path.exists(BRIEFING_DIR):
            print(f"  [{self.role}] Briefing directory not found: {BRIEFING_DIR}")
            return None

        briefing_files = sorted(
            glob.glob(os.path.join(BRIEFING_DIR, "briefing_*.md")),
            reverse=True
        )

        if not briefing_files:
            print(f"  [{self.role}] No briefing files found in {BRIEFING_DIR}")
            return None

        latest = briefing_files[0]
        try:
            with open(latest, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"  [{self.role}] Loaded briefing: {os.path.basename(latest)} ({len(content)} chars)")
            return content
        except Exception as e:
            print(f"  [{self.role}] Error reading briefing: {e}")
            return None

    # ── Content Curation ─────────────────────────────────────────

    def curate_from_briefing(
        self,
        briefing_text: str,
        audience_filter: Optional[str] = None,
        platform_filter: Optional[str] = None,
        feedback: Optional[str] = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate audience-targeted social media posts from a TrendScout briefing.

        Args:
            briefing_text: Raw TrendScout briefing content
            audience_filter: Optional persona ID to generate for only one audience
            platform_filter: Optional platform name to generate for only one platform
            feedback: Optional feedback string for refinement

        Returns:
            Nested dict: {audience_id: {platform: post_content}}
        """
        if not briefing_text or len(briefing_text) < 50:
            print(f"  [{self.role}] Briefing too short — skipping curation.")
            return {}

        all_posts: Dict[str, Dict[str, str]] = {}
        personas_to_process = {}

        if audience_filter:
            if audience_filter in self.personas:
                personas_to_process[audience_filter] = self.personas[audience_filter]
            else:
                print(f"  [{self.role}] Unknown audience: {audience_filter}")
                return {}
        else:
            personas_to_process = self.personas

        for persona_id, persona in personas_to_process.items():
            platforms = persona.get("platforms", ["facebook"])
            if platform_filter:
                platforms = [p for p in platforms if p == platform_filter]
                if not platforms:
                    continue

            print(f"  [{self.role}] Curating for: {persona['label']} → {platforms}")
            audience_posts = {}

            for platform in platforms:
                post = self._generate_post(briefing_text, persona, platform, feedback=feedback)
                if post:
                    audience_posts[platform] = post

            if audience_posts:
                all_posts[persona_id] = audience_posts

        print(f"  [{self.role}] Generated {sum(len(v) for v in all_posts.values())} posts "
              f"for {len(all_posts)} audiences.")
        return all_posts

    def curate_from_latest(
        self,
        audience_filter: Optional[str] = None,
        platform_filter: Optional[str] = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Convenience method: reads latest briefing and curates content.
        """
        briefing = self.get_latest_briefing()
        if not briefing:
            return {}
        return self.curate_from_briefing(briefing, audience_filter, platform_filter)

    def _generate_post(self, briefing: str, persona: Dict[str, Any], platform: str, feedback: Optional[str] = None) -> str:
        """Generate a single post for a specific audience × platform combination."""
        p_config = self.platform_config.get(platform, {})

        # Build the prompt
        if self.prompt_template:
            prompt = (
                self.prompt_template
                .replace("{briefing_content}", briefing[:4000])
                .replace("{audience_persona}", json.dumps(persona, ensure_ascii=False, indent=2))
                .replace("{target_platform}", platform)
                .replace("{platform_config}", json.dumps(p_config, ensure_ascii=False, indent=2))
            )
        else:
            # Inline fallback
            prompt = f"""
Bạn là ContentCurator. Hãy tạo 1 bài đăng {platform} cho đối tượng: {persona['label']}.

Báo cáo TrendScout:
{briefing[:3000]}

Tone: {persona.get('tone', 'professional')}
Hashtags: {', '.join(persona.get('hashtags', [])[:8])}
CTA: {persona.get('cta_style', 'Chia sẻ nếu thấy hữu ích')}
Max chars: {p_config.get('max_chars', 2000)}

CHỈ trả về nội dung bài đăng bằng tiếng Việt, không giải thích.
"""
        
        if feedback:
            prompt += f"\n\nCRITICAL FEEDBACK FROM PREVIOUS DRAFT:\n{feedback}\n\nPlease revise the content to address these points while maintaining the same persona and platform requirements."

        try:
            # Using L3 for refinement if feedback is provided to ensure high quality
            complexity = "L3" if feedback else "L2"
            post = llm.query(prompt, complexity=complexity, domain="content")
            if post:
                max_chars = p_config.get("max_chars", 2000)
                post = post.strip()[:max_chars]
                print(f"    ✅ [{persona.get('label_short', 'Social')}][{platform}] {len(post)} chars {'(Refined)' if feedback else ''}")
                return post
            else:
                print(f"    ❌ [{persona.get('label_short', 'Social')}][{platform}] Empty response")
                return ""
        except Exception as e:
            print(f"    ❌ [{persona.get('label_short', 'Social')}][{platform}] Error: {e}")
            return ""

    # ── Persistence ──────────────────────────────────────────────

    def save_curated_posts(self, posts: Dict[str, Dict[str, str]]) -> str:
        """
        Save curated posts as a JSON file for GrowthAgent to pick up.
        Returns the file path.
        """
        os.makedirs(CURATED_OUTPUT_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(CURATED_OUTPUT_DIR, f"curated_{timestamp}.json")

        data = {
            "id": f"curated_{timestamp}",
            "date": today,
            "created": datetime.now().isoformat(),
            "source": "trendscout_briefing",
            "status": "pending_approval",
            "posts": posts,
            "stats": {
                "audiences": len(posts),
                "total_posts": sum(len(v) for v in posts.values()),
            },
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  [{self.role}] Curated posts saved to {filepath}")
        except Exception as e:
            print(f"  [{self.role}] Error saving curated posts: {e}")

        return filepath

    # ── Full Pipeline ────────────────────────────────────────────

    def run_pipeline(
        self,
        briefing_text: Optional[str] = None,
        audience_filter: Optional[str] = None,
    ) -> Optional[str]:
        """
        Execute the full curation pipeline:
        1. Read latest briefing (or use provided text)
        2. Generate posts for all audiences × platforms
        3. Save to disk for GrowthAgent pickup

        Returns the saved file path, or None on failure.
        """
        print(f"\n{'='*60}")
        print(f"  [{self.role}] 🚀 Starting content curation pipeline...")
        print(f"  [{self.role}] Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}\n")

        # Step 1: Get briefing
        if not briefing_text:
            briefing_text = self.get_latest_briefing()
        if not briefing_text:
            print(f"  [{self.role}] No briefing available. Pipeline aborted.")
            return None

        # Step 2: Curate
        posts = self.curate_from_briefing(briefing_text, audience_filter)
        if not posts:
            print(f"  [{self.role}] No posts generated. Pipeline aborted.")
            return None

        # Step 3: Save
        filepath = self.save_curated_posts(posts)

        print(f"\n{'='*60}")
        print(f"  [{self.role}] ✅ Pipeline complete!")
        print(f"  [{self.role}] Posts saved: {filepath}")
        print(f"  [{self.role}] Audiences: {list(posts.keys())}")
        print(f"  [{self.role}] Total posts: {sum(len(v) for v in posts.values())}")
        print(f"{'='*60}\n")

        return filepath

    # ── Helpers ───────────────────────────────────────────────────

    def list_audiences(self) -> List[Dict[str, str]]:
        """Return available audience personas with metadata."""
        return [
            {
                "id": pid,
                "label": p.get("label", pid),
                "platforms": p.get("platforms", []),
                "tone": p.get("tone", ""),
            }
            for pid, p in self.personas.items()
        ]


# ─── LangGraph Node ────────────────────────────────────────────────

def content_curator_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node entry point.

    Reads user intent from messages to decide:
    - Full curation pipeline (default)
    - Audience-specific curation (if audience keyword detected)
    - List audiences
    """
    messages = state.get("messages", [])
    user_input = ""
    for msg in reversed(messages):
        if msg and isinstance(msg, str) and not msg.startswith("System:"):
            user_input = msg
            break

    user_input_lower = user_input.lower() if user_input else ""
    agent = ContentCuratorAgent()

    # Audience keyword detection
    audience_keywords = {
        "kế toán": "finance_professionals",
        "kiểm toán": "finance_professionals",
        "tài chính": "finance_professionals",
        "accountant": "finance_professionals",
        "auditor": "finance_professionals",
        "sinh viên": "finance_students",
        "student": "finance_students",
        "sv ": "finance_students",
        "giáo dục": "educators",
        "education": "educators",
        "giáo viên": "educators",
        "teacher": "educators",
        "giảng viên": "finance_educators",
        "lecturer": "finance_educators",
        "professor": "finance_educators",
        "gv dạy": "finance_educators",
    }

    # Check for audience list request
    if any(w in user_input_lower for w in ["danh sách", "list", "audience", "đối tượng"]):
        audiences = agent.list_audiences()
        audience_list = "\n".join([
            f"• **{a['label']}** → {', '.join(a['platforms'])}"
            for a in audiences
        ])
        return {
            "messages": [f"ContentCurator: 📋 Đối tượng mục tiêu:\n{audience_list}"]
        }

    # Check for specific audience
    target_audience = None
    for keyword, audience_id in audience_keywords.items():
        if keyword in user_input_lower:
            target_audience = audience_id
            break

    # If revision requested by Evaluator
    feedback = state.get("critic_feedback")
    if feedback and state.get("routing_category") == "revise_content":
        print(f"  [ContentCurator] Revising content based on feedback...")
        # For simplicity in this node, we'll refine the latest briefing content
        # with the provided feedback. In a more complex graph, we'd pass the draft itself.
        briefing = agent.get_latest_briefing()
        if briefing:
            # We target a general audience for the revision loop demo
            posts = agent.curate_from_briefing(briefing, feedback=feedback)
            filepath = agent.save_curated_posts(posts)
            return {
                "messages": [f"ContentCurator: ✅ Đã chỉnh sửa bài đăng dựa trên feedback.\n📁 File: {filepath}"],
                "critic_feedback": None # Reset feedback after revision
            }

    # Run pipeline
    filepath = agent.run_pipeline(audience_filter=target_audience)
    if filepath:
        return {
            "messages": [
                f"ContentCurator: ✅ Đã tạo bài đăng từ TrendScout briefing.\n"
                f"📁 File: {filepath}\n"
                f"Kiểm tra Telegram để duyệt và đăng bài."
            ]
        }
    else:
        return {
            "messages": [
                "ContentCurator: ⚠️ Không có dữ liệu TrendScout mới để tạo bài đăng. "
                "Hãy chạy TrendScout Agent trước."
            ]
        }


# ─── Standalone Execution ──────────────────────────────────────────
if __name__ == "__main__":
    print("Running ContentCurator Agent standalone...")
    agent = ContentCuratorAgent()

    print("\n--- Available Audiences ---")
    for a in agent.list_audiences():
        print(f"  • {a['label']} → {', '.join(a['platforms'])} (tone: {a['tone']})")

    print("\n--- Running Curation Pipeline ---")
    result = agent.run_pipeline()
    print(f"\nResult: {result}")
