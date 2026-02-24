import os
from firecrawl import FirecrawlApp
from core.state import AgentState
from core.utils.observability import obs

class FirecrawlAgent:
    """
    Advanced Web Scraper:
    Converts URLs or searches into clean Markdown using Firecrawl.
    Ideal for RAG as it removes navigation, ads, and boilerplate.
    """
    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            print("  [Firecrawl] Warning: API Key missing.")
        self.app = FirecrawlApp(api_key=api_key) if api_key else None

    def crawl_url(self, url: str) -> str:
        """Crawls a specific URL and returns Markdown."""
        if not self.app:
            return f"Firecrawl not configured. Cannot crawl {url}."
        
        print(f"  [Firecrawl] Crawling URL: {url}...")
        try:
            # We use scrape_url or crawl_url depending on the depth needed
            # For a single page (RAG context), scrape is usually enough
            result = self.app.scrape_url(url, params={'formats': ['markdown']})
            return result.get('markdown', 'No content found.')
        except Exception as e:
            return f"Error crawling {url}: {e}"

    def search_and_extract(self, query: str) -> str:
        """Searches the web and extracts the top result into Markdown."""
        if not self.app:
            return f"Firecrawl not configured. Cannot search for {query}."
        
        print(f"  [Firecrawl] Searching for: {query}...")
        try:
            # Firecrawl's search functionality is advanced
            # It returns structured results from multiple pages
            search_result = self.app.search(query, params={'limit': 3, 'scrapeOptions': {'formats': ['markdown']}})
            
            combined_md = ""
            for i, res in enumerate(search_result.get('data', [])):
                combined_md += f"\n--- Source {i+1}: {res.get('url')} ---\n"
                combined_md += res.get('markdown', 'No content.')
                combined_md += "\n"
            
            return combined_md if combined_md else "No results found."
        except Exception as e:
            return f"Error searching {query}: {e}"

def firecrawl_node(state: AgentState):
    """LangGraph node for clean web research."""
    user_input = state["messages"][-1] if state["messages"] else ""
    user_id = state.get("user_id", "default")
    
    trace_ctx = obs.start_trace(f"firecrawl_{user_id}", "firecrawl_research")
    
    agent = FirecrawlAgent()
    # Logic: If it looks like a URL, crawl it. Otherwise, search.
    if user_input.startswith("http"):
        results = agent.crawl_url(user_input)
    else:
        results = agent.search_and_extract(user_input)
    
    obs.end_trace(trace_ctx, {"query": user_input, "status": "success"})
    
    return {
        "browser_results": results,
        "messages": [f"Firecrawl (Clean Data): Extracted {len(results)} characters of Markdown."]
    }
