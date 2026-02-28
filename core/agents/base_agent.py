import json
from typing import Dict, Any, List, Optional
from core.state import AgentState
from core.utils.llm_manager import LLMManager
from core.utils.prompt_loader import PromptLoader
from core.utils.response_parser import parse_json_response
from core.utils.bot_logger import get_logger

logger = get_logger("base_agent")

class BaseAgent:
    """
    Base class for all Orchesta agents.
    Provides common functionality for LLM interaction, prompt loading, and response parsing.
    """
    name: str = "base_agent"
    prompt_file: Optional[str] = None
    default_complexity: str = "L2"
    domain: str = "general"
    tools: List[Any] = []

    def __init__(self, name: Optional[str] = None, prompt_file: Optional[str] = None):
        if name: self.name = name
        if prompt_file: self.prompt_file = prompt_file
        self.llm = LLMManager()
        self._system_prompt: Optional[str] = None

    @property
    def system_prompt(self) -> str:
        """Lazy-loaded and cached system prompt."""
        if self._system_prompt is None:
            if self.prompt_file:
                self._system_prompt = PromptLoader.load(self.prompt_file)
            else:
                self._system_prompt = f"You are the {self.name}."
        return self._system_prompt

    def extract_user_input(self, state: AgentState) -> str:
        """Extracts the most recent user message from state."""
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return msg.get("content", "")
            if isinstance(msg, str) and not msg.startswith("System:"):
                return msg
        return ""

    def query_llm(self, prompt: str, **kwargs) -> str:
        """Standardized LLM query with domain and complexity defaults."""
        complexity = kwargs.pop("complexity", self.default_complexity)
        domain = kwargs.pop("domain", self.domain)
        
        # Inject system prompt if not present in kwargs and not a simple query
        if "system_prompt" not in kwargs:
             full_prompt = f"System: {self.system_prompt}\n\nUser: {prompt}"
        else:
            full_prompt = prompt

        return self.llm.query(full_prompt, complexity=complexity, domain=domain, **kwargs) or ""

    def parse_json_response(self, response: str) -> dict:
        """Delegates to standardized response parser."""
        return parse_json_response(response)

    def process_request(self, state: AgentState) -> dict:
        """Override in subclass to implement specific logic."""
        raise NotImplementedError("Subclasses must implement process_request")

    def as_node(self):
        """Returns a LangGraph-compatible node function."""
        async def node_fn(state: AgentState):
            return await self.process_request(state)
        
        node_fn.__name__ = f"{self.name}_node"
        return node_fn
