import os
import requests
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("search_service")

class SearchService:
    """
    Utility to perform web searches using Firecrawl or other search APIs.
    Used to ground AI responses in real-time transit data.
    """
    def __init__(self):
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        self.base_url = "https://api.firecrawl.dev/v1/search"

    def search(self, query: str, limit: int = 5) -> str:
        """
        Performs a web search and returns a consolidated text context.
        """
        if not self.api_key:
            logger.warning("FIRECRAWL_API_KEY not found. Search disabled.")
            return ""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "query": query,
                "limit": limit,
                "lang": "vi"
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=15)
            response.raise_for_status()
            
            results = response.json().get("data", [])
            context_blocks = []
            for res in results:
                title = res.get("title", "")
                snippet = res.get("description", "")
                url = res.get("url", "")
                context_blocks.append(f"Title: {title}\nSnippet: {snippet}\nSource: {url}\n")
            
            return "\n".join(context_blocks)
        except Exception as e:
            logger.error(f"SearchService error: {e}")
            return ""

if __name__ == "__main__":
    s = SearchService()
    print(s.search("Xe bus từ Vinhomes Ocean Park đến Mỹ Đình"))
