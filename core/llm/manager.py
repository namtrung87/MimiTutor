import os
import asyncio
import litellm
from typing import List, Dict, Any, Optional
from core.utils.bot_logger import get_logger
from .usage_stats import UsageStats
from .token_monitor import TokenMonitor
from .context_pruner import ContextPruner
from core.utils.llm_config import llm_config

logger = get_logger("llm_manager")

class LLMManager:
    """
    Unified LLM Manager using LiteLLM for routing and Langfuse for observability.
    Standardizes cross-provider calls (Gemini, Groq, Cerebras, etc.).
    """
    def __init__(self, app_name: str = "orchesta_assistant"):
        self.app_name = app_name
        self.langfuse_handler = None
        self._setup_langfuse()
        
        # Issue 9: Initialize KeyManager for rotation
        gemini_keys_env = os.environ.get("GEMINI_API_KEY", "")
        self.key_manager = KeyManager(gemini_keys_env.split(","))

    def _get_api_key(self, provider: str) -> Optional[str]:
        if provider == "gemini":
            return self.key_manager.get_key()
        return os.environ.get(f"{provider.upper()}_API_KEY")

    def _setup_langfuse(self):
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            try:
                from langfuse.callback import CallbackHandler
                self.langfuse_handler = CallbackHandler(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
                )
                logger.info(f"Langfuse tracing ENABLED for {self.app_name}.")
            except ImportError:
                logger.warning("Langfuse module not found.")
        else:
            logger.info("Langfuse keys missing. Tracing DISABLED.")

    def query_sync(self, prompt: str, complexity: str = "auto", domain: str = "auto", model_override: Optional[str] = None, messages: Optional[List[Dict[str, str]]] = None, **kwargs) -> Optional[str]:
        """Synchronous wrapper for query(). Safe to call from sync LangGraph nodes."""
        import time
        start_time = time.time()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.query(prompt, complexity, domain, model_override, messages, **kwargs)
            )
            loop.close()
            duration = time.time() - start_time
            logger.info(f"  [LLMManager] query_sync completed in {duration:.2f}s")
            return result
        except Exception as e:
            logger.error(f"query_sync error: {e}")
            return None

    async def query(self, prompt: str, complexity: str = "auto", domain: str = "auto", model_override: Optional[str] = None, messages: Optional[List[Dict[str, str]]] = None, **kwargs) -> Optional[str]:
        # 1. Pruning & Quota Check
        if messages:
             messages = ContextPruner.compact_context(messages)
        else:
             prompt = ContextPruner.prune_text(prompt)
             messages = [{"role": "user", "content": prompt}]

        is_budget_ok = UsageStats.is_within_budget()
        
        model = model_override
        if not model:
            if not is_budget_ok:
                logger.warning(f"  [LLMManager] Budget limit reached. Downgrading complexity '{complexity}' to Flash-Lite.")
                model = "gemini/gemini-2.0-flash-lite"
            else:
                if complexity == "L1": model = "gemini/gemini-2.0-flash-lite"
                elif complexity == "L3": model = "gemini/gemini-2.5-flash"
                else: model = "gemini/gemini-2.5-flash"

        # Check if provider is enabled
        provider = model.split("/")[0] if "/" in model else "gemini"
        if not llm_config.is_enabled(self.app_name, provider):
            logger.warning(f"  [LLMManager] Provider '{provider}' is disabled for '{self.app_name}'. Falling back to Gemini.")
            model = "gemini/gemini-2.0-flash"
            provider = "gemini"

        api_key = self._get_api_key(provider)

        logger.info(f"Querying: {model} ({complexity}){' [BUDGET DOWNGRADE]' if not is_budget_ok and not model_override else ''}")
        
        max_retries = 2 if domain == "tutor" else 3
        for attempt in range(max_retries):
            try:
                callbacks = [self.langfuse_handler] if self.langfuse_handler else []
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    api_key=api_key,
                    metadata={"complexity": complexity, "domain": domain, "app": self.app_name},
                    callbacks=callbacks,
                    **kwargs
                )
                content = response.choices[0].message.content
                
                # 2. Extract usage and log
                usage = response.usage
                UsageStats.log_usage(model, usage.prompt_tokens, usage.completion_tokens)
                
                # 3. Token Monitor Check
                if TokenMonitor.check_and_interrupt(complexity, usage.total_tokens):
                    logger.warning(f"  [LLMManager] Quota exceeded for {complexity}: {usage.total_tokens} tokens.")
                
                return content
            except Exception as e:
                logger.error(f"LiteLLM Error (Attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    # Final fallback if primary fails
                    if model.startswith("gemini"):
                        fallback_model = "groq/llama-3.3-70b-versatile"
                        logger.warning(f"  [LLMManager] Gemini failure ({e}). Falling back to {fallback_model}.")
                        return await self.query(prompt, complexity="L1", model_override=fallback_model)
                    
                    if model != "gemini/gemini-2.0-flash-lite":
                        logger.warning(f"  [LLMManager] Critical failure ({e}). Falling back to safety model.")
                        return await self.query(prompt, complexity="L1", model_override="gemini/gemini-2.0-flash-lite")
                    return f"ERROR: LLM failure - {e}"

    async def batch_query(self, prompts: List[str], models: List[str]) -> List[Optional[str]]:
        """Executes multiple queries in parallel."""
        tasks = []
        for i, prompt in enumerate(prompts):
            model = models[i] if i < len(models) else models[-1]
            tasks.append(self.query(prompt, model_override=model))
        return list(await asyncio.gather(*tasks))

    def query_tools(self, prompt: str, tools: List[Dict[str, Any]], model: str = "gemini/gemini-1.5-pro") -> Any:
        try:
            logger.info(f"Tool Call: {model}")
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                tool_choice="auto",
                callbacks=[self.langfuse_handler] if self.langfuse_handler else []
            )
            return response
        except Exception as e:
            logger.error(f"LiteLLM Tool error: {e}")
            return None

    def embed(self, text: str, model: str = "text-embedding-004") -> Optional[List[float]]:
        try:
            # LiteLLM uses 'google/' prefix for Gemini embeddings
            response = litellm.embedding(model=f"google/{model}", input=[text])
            return response.data[0]['embedding']
        except Exception as e:
            logger.error(f"LiteLLM Embedding error: {e}")
            return None

    def run_startup_health_check(self):
        logger.info(f"LiteLLM Status: READY. Langfuse: {'ENABLED' if self.langfuse_handler else 'DISABLED'}")

class KeyManager:
    """
    Utility for managing and rotating multiple API keys.
    """
    def __init__(self, keys: List[str]):
        self.keys = [k.strip() for k in keys if k.strip()]
        self.current_idx = 0
        
    def get_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.keys)
        return key

    def get_all_keys(self) -> List[str]:
        return self.keys
