"""
TrendScout Agent: Daily KOL & Trend Intelligence
==================================================
Monitors KOLs and trend sources across multiple domains,
generates daily Vietnamese briefings with actionable recommendations.

Domains:
  - AI & Tech
  - Accounting / Auditing / Finance
  - Education & EdTech
  - Gamification & Game-Based Learning
"""
import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from core.state import AgentState
from core.utils.llm_manager import LLMManager

llm = LLMManager()

# ─── Paths ─────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
REGISTRY_PATH = os.path.join(BASE_DIR, "11_Personal_Learning", "sources", "kol_registry.json")
PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "trendscout_daily_briefing.md")
BRIEFING_OUTPUT_DIR = os.path.join(BASE_DIR, "11_Personal_Learning", "summaries")

# ─── Firecrawl (optional) ──────────────────────────────────────────
try:
    from core.agents.firecrawl_agent import FirecrawlAgent
    _firecrawl_available = True
except ImportError:
    _firecrawl_available = False


class TrendScoutAgent:
    """
    Agent responsible for scanning KOL sources and producing
    a structured daily intelligence briefing.
    """

    def __init__(self):
        self.role = "TrendScout Intelligence Officer"
        self.registry: Dict[str, Any] = {}
        self.prompt_template: str = ""
        self._load_resources()

    # ── Resource Loading ───────────────────────────────────────────

    def _load_resources(self):
        """Load KOL registry and prompt template from disk."""
        self.registry = self.load_kol_registry()
        self.prompt_template = self._load_prompt_template()

    def load_kol_registry(self) -> Dict[str, Any]:
        """
        Load the KOL / source registry from JSON.
        Returns the full registry dict or an empty dict on error.
        """
        if not os.path.exists(REGISTRY_PATH):
            print(f"  [{self.role}] Warning: Registry not found at {REGISTRY_PATH}")
            return {}
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"  [{self.role}] Loaded registry v{data.get('version', '?')}: "
                  f"{sum(len(d.get('sources', [])) for d in data.get('domains', {}).values())} sources")
            return data
        except Exception as e:
            print(f"  [{self.role}] Error loading registry: {e}")
            return {}

    def _load_prompt_template(self) -> str:
        """Load the briefing prompt template from disk."""
        if not os.path.exists(PROMPT_PATH):
            print(f"  [{self.role}] Warning: Prompt template not found at {PROMPT_PATH}")
            return ""
        try:
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"  [{self.role}] Error loading prompt: {e}")
            return ""

    # ── Source Scanning ────────────────────────────────────────────

    def _get_sources(self, domain_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns a flat list of sources, optionally filtered by domain key.
        """
        domains = self.registry.get("domains", {})
        sources: List[Dict[str, Any]] = []
        for domain_key, domain_data in domains.items():
            if domain_filter and domain_key != domain_filter:
                continue
            for src in domain_data.get("sources", []):
                sources.append({**src, "domain": domain_key, "domain_label": domain_data.get("label", domain_key)})
        return sources

    def scan_sources(self, domain_filter: Optional[str] = None) -> str:
        """
        Scan KOL sources for recent content.
        Uses Firecrawl if available, otherwise falls back to LLM-based web search.
        
        Returns concatenated raw content string.
        """
        sources = self._get_sources(domain_filter)
        max_sources = self.registry.get("scan_config", {}).get("max_sources_per_run", 10)

        # Prioritise diversity: pick up to max_sources spread across domains
        if len(sources) > max_sources:
            random.shuffle(sources)
            sources = sources[:max_sources]

        print(f"  [{self.role}] Scanning {len(sources)} sources...")
        raw_chunks: List[str] = []

        for src in sources:
            url = src.get("url", "")
            name = src.get("name", "Unknown")
            domain_label = src.get("domain_label", "")
            platform = src.get("platform", "")
            print(f"    → [{domain_label}] {name}: {url} (Platform: {platform})")

            content = self._fetch_source(name, url, platform)
            if content:
                header = f"\n{'='*60}\nSOURCE: {name} ({domain_label})\nURL: {url}\n{'='*60}\n"
                raw_chunks.append(header + content[:3000])  # Cap per source

        combined = "\n".join(raw_chunks)
        print(f"  [{self.role}] Collected {len(combined)} chars from {len(raw_chunks)} sources.")
        return combined

    def _fetch_source(self, name: str, url: str, platform: str = "") -> str:
        """Fetch content from a single source URL."""
        # Strategy 1: Use Firecrawl for clean Markdown extraction
        if _firecrawl_available and platform != "search":
            try:
                crawler = FirecrawlAgent()
                if crawler.app:
                    result = crawler.crawl_url(url)
                    if result and not result.startswith("Error"):
                        return result
            except Exception as e:
                print(f"    [Firecrawl fallback] {name}: {e}")

        # Strategy 2: Google News RSS fallback (Real-time data)
        try:
            import urllib.request
            import urllib.parse
            import xml.etree.ElementTree as ET
            
            # Use name as query to find relevant news
            query = urllib.parse.quote(f"{name} when:7d")
            url_rss = f"https://news.google.com/rss/search?q={query}"
            
            req = urllib.request.Request(url_rss, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req, timeout=10).read()
            root = ET.fromstring(html)
            
            items = root.findall('.//item')[:5]
            if not items:
                return "No recent updates found on Google News."
                
            snippets = []
            for item in items:
                title = item.find('title').text if item.find('title') is not None else 'No title'
                link = item.find('link').text if item.find('link') is not None else 'No link'
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else 'Unknown date'
                snippets.append(f"- {title} ({pubDate})\n  Link: {link}")
                
            return "Recent news:\n" + "\n".join(snippets)
        except Exception as e:
            print(f"    [RSS fallback failed] {name}: {e}")
            return ""

    # ── Briefing Generation ────────────────────────────────────────

    def generate_daily_briefing(self, raw_content: Optional[str] = None) -> str:
        """
        Generate a structured daily briefing from raw source content.
        If raw_content is not provided, will scan sources first.
        """
        if not raw_content:
            raw_content = self.scan_sources()

        if not raw_content or len(raw_content) < 50:
            return "📡 TrendScout: Không có dữ liệu mới hôm nay. Các nguồn sẽ được quét lại vào ngày mai."

        today = datetime.now().strftime("%Y-%m-%d")

        # Build the prompt from template
        if self.prompt_template:
            prompt = self.prompt_template.replace("{raw_content}", raw_content).replace("{date}", today)
        else:
            # Inline fallback prompt
            prompt = f"""
            You are TrendScout, a trend intelligence expert.
            Analyze the following raw data from KOL sources and create a Daily Briefing in Vietnamese.

            RAW DATA:
            {raw_content}

            OUTPUT FORMAT:
            # 📡 TrendScout Daily Briefing — {today}

            ## 🔥 Top 5 Xu hướng nổi bật
            (Each with: name, source, 2-3 sentence summary, impact score 1-10)

            ## 🧠 Mindset Changers
            (2-3 mindset-shifting ideas from KOLs)

            ## 🛠️ Đề xuất cải thiện hệ thống Orchesta
            (2-3 specific agent/workflow improvement suggestions)

            ## 📊 Domain Breakdown
            ### AI & Công nghệ
            ### Kế toán – Kiểm toán – Tài chính
            ### Giáo dục & EdTech
            ### Gamification

            ## 🔗 Links hữu ích
            """

        print(f"  [{self.role}] Generating daily briefing for {today}...")
        briefing = llm.query(prompt, complexity="L2", domain="research")

        # Save briefing to disk
        self._save_briefing(briefing, today)

        return briefing

    def _save_briefing(self, briefing: str, date_str: str):
        """Persist the briefing as a Markdown file."""
        os.makedirs(BRIEFING_OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(BRIEFING_OUTPUT_DIR, f"briefing_{date_str}.md")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(briefing)
            print(f"  [{self.role}] Briefing saved to {filepath}")
        except Exception as e:
            print(f"  [{self.role}] Error saving briefing: {e}")

    # ── Domain-specific Helpers ────────────────────────────────────

    def get_domain_summary(self, domain_key: str) -> str:
        """Generate a focused briefing for a single domain."""
        raw = self.scan_sources(domain_filter=domain_key)
        if not raw:
            return f"Không có cập nhật mới cho domain: {domain_key}"

        domains = self.registry.get("domains", {})
        label = domains.get(domain_key, {}).get("label", domain_key)
        today = datetime.now().strftime("%Y-%m-%d")

        # Load domain template
        template_path = os.path.join(BASE_DIR, "prompts", "trendscout_domain_report.md")
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        else:
            prompt_template = "You are TrendScout. Create a focused report for {label}."

        prompt = prompt_template.format(label=label, today=today, raw=raw)

        return llm.query(prompt, complexity="L2", domain="research")

    def list_domains(self) -> List[Dict[str, str]]:
        """Return available domains with labels and source counts."""
        domains = self.registry.get("domains", {})
        return [
            {
                "key": k,
                "label": v.get("label", k),
                "source_count": len(v.get("sources", []))
            }
            for k, v in domains.items()
        ]


# ─── LangGraph Node ────────────────────────────────────────────────

def trendscout_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node entry point.
    
    Reads user intent from messages to decide:
    - Full daily briefing (default)
    - Domain-specific report (if domain keyword detected)
    - List available domains
    """
    messages = state.get("messages", [])
    user_input = ""
    for msg in reversed(messages):
        if msg and isinstance(msg, str) and not msg.startswith("System:"):
            user_input = msg
            break

    user_input_lower = user_input.lower() if user_input else ""
    agent = TrendScoutAgent()

    # Check for domain-specific request
    domain_keywords = {
        "ai": "ai_tech",
        "công nghệ": "ai_tech",
        "tech": "ai_tech",
        "kế toán": "accounting_audit_finance",
        "kiểm toán": "accounting_audit_finance",
        "tài chính": "accounting_audit_finance",
        "audit": "accounting_audit_finance",
        "finance": "accounting_audit_finance",
        "accounting": "accounting_audit_finance",
        "giáo dục": "education",
        "education": "education",
        "edtech": "education",
        "gamification": "gamification",
        "game": "gamification",
    }

    # Check for domain list request
    if any(w in user_input_lower for w in ["domain", "danh sách", "list", "nguồn"]):
        domains = agent.list_domains()
        domain_list = "\n".join([f"• **{d['label']}** ({d['source_count']} nguồn)" for d in domains])
        return {
            "messages": [f"TrendScout Agent: 📋 Các domain đang theo dõi:\n{domain_list}"]
        }

    # Check for specific domain
    target_domain = None
    for keyword, domain_key in domain_keywords.items():
        if keyword in user_input_lower:
            target_domain = domain_key
            break

    if target_domain:
        report = agent.get_domain_summary(target_domain)
        return {"messages": [f"TrendScout Agent: {report}"]}

    # Default: full daily briefing
    briefing = agent.generate_daily_briefing()
    return {"messages": [f"TrendScout Agent: {briefing}"]}


# ─── Standalone Execution ──────────────────────────────────────────
if __name__ == "__main__":
    print("Running TrendScout Agent standalone...")
    agent = TrendScoutAgent()
    
    print("\n--- Available Domains ---")
    for d in agent.list_domains():
        print(f"  • {d['label']} ({d['source_count']} sources)")
    
    print("\n--- Generating Daily Briefing ---")
    briefing = agent.generate_daily_briefing()
    print(f"\n{briefing}")
