"""
GrowthAgent: Automated Social Media Content Pipeline for Vietnam Market.

Pipeline: Mine Content → AI Draft → Telegram Approval → n8n Publish
Platforms: Facebook, Zalo OA, TikTok, Telegram Channel
"""
import os
import json
import glob
import asyncio
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.state import AgentState
from core.utils.llm_manager import LLMManager

# Lazy imports for optional dependencies
try:
    from core.services.telegram_service import telegram_service
except ImportError:
    telegram_service = None

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
except ImportError:
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None
    Bot = None


# ─── Content Pillars ───────────────────────────────────────────────
CONTENT_PILLARS = [
    "ai_leadership",      # AI-First Leadership, Orchestra Assistant
    "academic_excellence", # PhD, Teaching, Research
    "gamification_tech",   # Gamification projects, game development
    "trend_sharing",       # TrendScout → curated posts for personal branding
]

# ─── Platform Configs ──────────────────────────────────────────────
PLATFORMS = {
    "facebook": {
        "max_chars": 2000,
        "tone": "professional_engaging",
        "language": "vi",
        "format": "post_with_cta",
    },
    "zalo_oa": {
        "max_chars": 1500,
        "tone": "friendly_helpful",
        "language": "vi",
        "format": "article_brief",
    },
    "tiktok": {
        "max_chars": 300,
        "tone": "catchy_viral",
        "language": "vi",
        "format": "caption_with_hashtags",
    },
    "telegram": {
        "max_chars": 4096,
        "tone": "direct_insightful",
        "language": "vi",
        "format": "channel_update",
    },
    "discord": {
        "max_chars": 2000,
        "tone": "casual_informative",
        "language": "vi",
        "format": "community_update",
    },
}

# ─── Source Directories for Content Mining ─────────────────────────
CONTENT_SOURCES = {
    "ai_leadership": [
        "research_results",
        "core/agents",
    ],
    "academic_excellence": [
        "01_Academic_Success",
        "02_Research_Scholarship",
    ],
    "gamification_tech": [
        "06_Gamification_Tech",
    ],
    "trend_sharing": [
        "08_Growth_Branding/curated",
    ],
}


class GrowthAgent:
    """
    Orchestrates the automated social media content pipeline.
    
    Usage:
        agent = GrowthAgent()
        drafts = await agent.run_pipeline()
        # Drafts are sent to Telegram for approval
        # On approval, agent.publish(draft_id) posts via n8n
    """
    
    def __init__(self, base_dir: str = None):
        self.llm = LLMManager(app_name="mimi_hometutor")
        self.base_dir = Path(base_dir or os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.drafts_dir = self.base_dir / "08_Growth_Branding" / "drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.n8n_webhook_url = os.getenv("N8N_SOCIAL_WEBHOOK_URL", os.getenv("N8N_SKILL_WEBHOOK_URL"))
        
        # Load the growth prompt template
        prompt_path = self.base_dir / "prompts" / "growth_branding_specialist.md"
        self.system_prompt = ""
        if prompt_path.exists():
            self.system_prompt = prompt_path.read_text(encoding="utf-8")
    
    # ─── Phase 1: Content Mining ───────────────────────────────────
    def mine_content(self, pillar: str = None) -> List[Dict[str, Any]]:
        """Scan project directories for recent changes/new content."""
        sources = []
        pillars = [pillar] if pillar else CONTENT_PILLARS
        
        for p in pillars:
            dirs = CONTENT_SOURCES.get(p, [])
            for rel_dir in dirs:
                full_path = self.base_dir / rel_dir
                if not full_path.exists():
                    continue
                
                # Find recently modified files (last 48 hours)
                cutoff = datetime.datetime.now().timestamp() - (48 * 3600)
                for ext in ["*.md", "*.py", "*.txt", "*.json"]:
                    for fpath in full_path.rglob(ext):
                        try:
                            if fpath.stat().st_mtime > cutoff:
                                content = fpath.read_text(encoding="utf-8", errors="ignore")[:2000]
                                sources.append({
                                    "pillar": p,
                                    "file": str(fpath.relative_to(self.base_dir)),
                                    "snippet": content,
                                    "modified": datetime.datetime.fromtimestamp(fpath.stat().st_mtime).isoformat(),
                                })
                        except Exception:
                            continue
        
        print(f"  [GrowthAgent] Mined {len(sources)} content sources.")
        return sources
    
    # ─── Phase 2: AI Drafting ──────────────────────────────────────
    def generate_drafts(self, sources: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate platform-specific drafts from mined content."""
        if not sources:
            print("  [GrowthAgent] No new content to draft from.")
            return {}
        
        # Summarize sources for the prompt
        source_summary = "\n".join([
            f"- [{s['pillar']}] {s['file']}: {s['snippet'][:300]}..."
            for s in sources[:5]  # Limit to top 5 sources
        ])
        
        drafts = {}
        for platform, config in PLATFORMS.items():
            prompt = f"""
{self.system_prompt}

BẠN LÀ GROWTH AGENT. Tạo 1 bài đăng cho nền tảng: {platform.upper()}

QUY TẮC:
- Ngôn ngữ: Tiếng Việt
- Tone: {config['tone']}
- Tối đa {config['max_chars']} ký tự
- Format: {config['format']}
- PHẢI có Call-to-Action rõ ràng
- Hashtags phù hợp (nếu là TikTok/Facebook)
- Không dùng emoji quá nhiều (tối đa 3-4)

NGUỒN NỘI DUNG GẦN ĐÂY:
{source_summary}

HÃY VIẾT BÀI ĐĂNG (CHỈ trả về nội dung bài đăng, không giải thích):
"""
            try:
                draft = self.llm.query(prompt, complexity="L2")
                if draft:
                    # Truncate to max chars
                    drafts[platform] = draft[:config["max_chars"]]
                    print(f"  [GrowthAgent] ✅ Draft created for {platform} ({len(draft)} chars)")
                else:
                    print(f"  [GrowthAgent] ❌ Failed to generate draft for {platform}")
            except Exception as e:
                print(f"  [GrowthAgent] Error drafting for {platform}: {e}")
        
        return drafts
    
    # ─── Phase 3: Save & Send for Approval ─────────────────────────
    async def send_for_approval(self, drafts: Dict[str, str]) -> Optional[str]:
        """Save drafts and send to Telegram for user approval."""
        if not drafts:
            return None
        
        # Save drafts to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_id = f"draft_{timestamp}"
        draft_file = self.drafts_dir / f"{draft_id}.json"
        
        draft_data = {
            "id": draft_id,
            "created": datetime.datetime.now().isoformat(),
            "status": "pending_approval",
            "drafts": drafts,
        }
        
        with open(draft_file, "w", encoding="utf-8") as f:
            json.dump(draft_data, f, ensure_ascii=False, indent=2)
        
        print(f"  [GrowthAgent] Drafts saved to {draft_file}")
        
        # Build Telegram approval message
        preview_lines = []
        for platform, content in drafts.items():
            icon = {"facebook": "🔵", "zalo_oa": "🟢", "tiktok": "⬛", "telegram": "📱", "discord": "👾"}.get(platform, "📄")
            preview = content[:150].replace("\n", " ")
            preview_lines.append(f"{icon} {platform.upper()}:\n{preview}...")
        
        approval_msg = (
            f"📝 *GrowthAgent: Bài viết mới cần duyệt*\n"
            f"ID: `{draft_id}`\n\n"
            + "\n\n".join(preview_lines)
            + f"\n\n💡 Reply với:\n"
            f"• `OK {draft_id}` → Đăng tất cả\n"
            f"• `SKIP {draft_id}` → Bỏ qua\n"
            f"• `EDIT {draft_id}` → Chỉnh sửa"
        )
        
        # Send via Telegram
        if telegram_service and telegram_service.bot:
            try:
                await telegram_service.send_message(approval_msg)
                print(f"  [GrowthAgent] 📱 Approval request sent to Telegram.")
            except Exception as e:
                print(f"  [GrowthAgent] Telegram send error: {e}")
        else:
            print(f"  [GrowthAgent] Telegram not configured. Draft saved locally: {draft_file}")
        
        return draft_id
    
    # ─── Phase 4: Publish via n8n ──────────────────────────────────
    async def publish(self, draft_id: str) -> Dict[str, Any]:
        """Publish approved drafts via n8n webhooks."""
        draft_file = self.drafts_dir / f"{draft_id}.json"
        
        if not draft_file.exists():
            return {"error": f"Draft {draft_id} not found"}
        
        with open(draft_file, "r", encoding="utf-8") as f:
            draft_data = json.load(f)
        
        if draft_data.get("status") == "published":
            return {"error": f"Draft {draft_id} already published"}
        
        results = {}
        
        if self.n8n_webhook_url:
            import httpx
            async with httpx.AsyncClient() as client:
                for platform, content in draft_data["drafts"].items():
                    payload = {
                        "action": f"social_media_post_{platform}",
                        "platform": platform,
                        "content": content,
                        "draft_id": draft_id,
                        "timestamp": datetime.datetime.now().isoformat(),
                    }
                    
                    try:
                        response = await client.post(
                            self.n8n_webhook_url,
                            json=payload,
                            timeout=30.0
                        )
                        response.raise_for_status()
                        results[platform] = {"status": "published", "response": response.json()}
                        print(f"  [GrowthAgent] ✅ Published to {platform}")
                    except Exception as e:
                        results[platform] = {"status": "error", "error": str(e)}
                        print(f"  [GrowthAgent] ❌ Failed to publish to {platform}: {e}")
        else:
            # Simulation mode
            for platform in draft_data["drafts"]:
                results[platform] = {"status": "simulated", "message": "n8n webhook not configured"}
            print(f"  [GrowthAgent] ⚠️ N8N_SOCIAL_WEBHOOK_URL not set. Running in simulation mode.")
        
        # Update draft status
        draft_data["status"] = "published"
        draft_data["publish_results"] = results
        draft_data["published_at"] = datetime.datetime.now().isoformat()
        
        with open(draft_file, "w", encoding="utf-8") as f:
            json.dump(draft_data, f, ensure_ascii=False, indent=2)
        
        return results
    
    # ─── Full Pipeline ─────────────────────────────────────────────
    async def run_pipeline(self, pillar: str = None) -> Optional[str]:
        """Execute the full content pipeline: Mine → Draft → Approve."""
        print(f"\n{'='*60}")
        print(f"  [GrowthAgent] 🚀 Starting content pipeline...")
        print(f"  [GrowthAgent] Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}\n")
        
        # Step 1: Mine
        sources = self.mine_content(pillar)
        if not sources:
            print("  [GrowthAgent] No new content found. Pipeline complete.")
            return None
        
        # Step 2: Draft
        drafts = self.generate_drafts(sources)
        
        # Step 3: Send for approval
        draft_id = await self.send_for_approval(drafts)
        
        return draft_id


# ─── LangGraph Node ────────────────────────────────────────────────
def growth_agent_node(state: AgentState) -> dict:
    """Entry point for the supervisor to call the growth agent."""
    agent = GrowthAgent()
    
    user_input = state.get("user_input", "") or (state["messages"][-1] if state.get("messages") else "")
    
    # Determine action from user input
    input_lower = str(user_input).lower()
    
    if "publish" in input_lower or "đăng" in input_lower:
        # Extract draft_id from input
        parts = str(user_input).split()
        draft_id = None
        for part in parts:
            if part.startswith("draft_"):
                draft_id = part
                break
        
        if draft_id:
            result = asyncio.run(agent.publish(draft_id))
            return {
                "messages": [f"GrowthAgent: Published draft {draft_id}. Results: {json.dumps(result, ensure_ascii=False)}"],
            }
        else:
            return {
                "messages": ["GrowthAgent: Vui lòng cung cấp draft_id để đăng bài. VD: 'Đăng draft_20260220_070000'"],
            }
    else:
        # Run full pipeline
        draft_id = asyncio.run(agent.run_pipeline())
        if draft_id:
            return {
                "messages": [f"GrowthAgent: Pipeline hoàn tất. Draft ID: {draft_id}. Kiểm tra Telegram để duyệt."],
            }
        else:
            return {
                "messages": ["GrowthAgent: Không tìm thấy nội dung mới để tạo bài viết."],
            }


# ─── Standalone Execution ──────────────────────────────────────────
if __name__ == "__main__":
    print("Running GrowthAgent pipeline standalone...")
    agent = GrowthAgent()
    result = asyncio.run(agent.run_pipeline())
    print(f"\nResult: {result}")
