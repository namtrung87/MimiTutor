import os
import requests
import time
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv
from core.utils.observability import obs

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

load_dotenv()

class ContextPruner:
    """Optimizes tokens by truncating/summarizing context."""
    @staticmethod
    def prune_messages(messages: List[str], max_tokens: int = 4000) -> List[str]:
        # Simple heuristic: 1 token ~= 4 chars
        current_chars = 0
        pruned = []
        for msg in reversed(messages):
            msg_len = len(msg)
            if current_chars + msg_len > max_tokens * 4:
                break
            pruned.insert(0, msg)
            current_chars += msg_len
        return pruned

    @staticmethod
    def prune_text(text: str, max_tokens: int = 1000) -> str:
        if len(text) <= max_tokens * 4:
            return text
        return text[:max_tokens * 4] + "... [TRUNCATED]"

    @staticmethod
    def compact_context(messages: List[str], max_tokens: int = 10000) -> List[str]:
        """
        Simulates Opus 4.6 context compaction by summarizing older history
        to fit into a smaller, more efficient context while keeping key facts.
        """
        if len(messages) <= 3:
            return messages
        
        # Keep the latest message and 2 previous for immediate context
        recent = messages[-3:]
        older = messages[:-3]
        
        # Create a summary of older messages (Mocked for now, in reality,
        # we'd use a cheap L1/L2 model for this)
        summary_prompt = f"Summarize the following interaction briefly to preserve context: {' '.join(older)}"
        # In a real implementation, we'd call llm.query(summary_prompt, complexity='L1')
        summary = f"[CONTEXT SUMMARY]: The conversation previously discussed {' '.join(older)[:500]}..."
        
        return [summary] + recent

class LLMProvider:
    def query(self, prompt: str) -> str:
        raise NotImplementedError

class KeyManager:
    """
    Manages API keys with load balancing and cooldown logic.
    """
    def __init__(self, keys: List[str], cooldown_seconds=60):
        self.keys = [k.strip() for k in keys if k.strip()]
        self.key_status = {k: {"status": "active", "cooldown_until": 0, "usage": 0} for k in self.keys}
        self.cooldown_seconds = cooldown_seconds
        self.current_index = 0

    def get_key(self) -> Optional[str]:
        if not self.keys: return None
        
        # Try finding an active key (Round Robin)
        start_index = self.current_index
        while True:
            key = self.keys[self.current_index]
            meta = self.key_status[key]
            
            # Check cooldown
            if meta["status"] == "cooldown":
                if time.time() > meta["cooldown_until"]:
                    print(f"  [KeyManager] Key {key[:5]}... exited cooldown.")
                    meta["status"] = "active"
                    meta["cooldown_until"] = 0
                else:
                    # Skip this key
                    self.current_index = (self.current_index + 1) % len(self.keys)
                    if self.current_index == start_index:
                        # All keys in cooldown
                        print(f"  [KeyManager] All keys are in cooldown!")
                        return None
                    continue
            
            # Key is active
            self.current_index = (self.current_index + 1) % len(self.keys)
            meta["usage"] += 1
            return key

    def report_error(self, key: str, error_msg: str):
        if "429" in error_msg or "quota" in error_msg.lower():
            print(f"  [KeyManager] Key {key[:5]}... hit Rate Limit (429). Cooling down for {self.cooldown_seconds}s.")
            self.key_status[key]["status"] = "cooldown"
            self.key_status[key]["cooldown_until"] = time.time() + self.cooldown_seconds

# Global health cache for LocalProvider to prevent redundant checks during import-heavy startups
_LOCAL_HEALTH_CACHE = {"is_healthy": None, "last_check": 0}

class LocalProvider(LLMProvider):
    def __init__(self, model="deepseek-r1:7b", base_url="http://localhost:11434/api/generate"):
        self.model = model
        self.base_url = base_url
        self.is_healthy = False
        self._check_health()

    def _check_health(self):
        global _LOCAL_HEALTH_CACHE
        now = time.time()
        
        # Reuse cache if checked within last 30 seconds (more frequent for fallback reliability)
        if _LOCAL_HEALTH_CACHE["is_healthy"] is not None and (now - _LOCAL_HEALTH_CACHE["last_check"]) < 30:
            self.is_healthy = _LOCAL_HEALTH_CACHE["is_healthy"]
            return

        try:
            # Simple check to see if Ollama is responsive (listing tags)
            res = requests.get(self.base_url.replace("/generate", "/tags"), timeout=2)
            if res.status_code == 200:
                self.is_healthy = True
                # Check if specific model exists
                models = [m["name"] for m in res.json().get("models", [])]
                if self.model not in models and f"{self.model}:latest" not in models:
                    print(f"  [LocalProvider] WARN: Model {self.model} not found in Ollama. Will attempt to run anyway.")
            else:
                self.is_healthy = False
        except:
            self.is_healthy = False
        
        _LOCAL_HEALTH_CACHE["is_healthy"] = self.is_healthy
        _LOCAL_HEALTH_CACHE["last_check"] = now

        if not self.is_healthy:
            print(f"  [LocalProvider] INFO: Ollama at {self.base_url} is OFFLINE. Local fallback disabled.")

    def query(self, prompt: str) -> str:
        if not self.is_healthy:
            self._check_health() # Re-check before giving up
            if not self.is_healthy: return None
            
        try:
            print(f"  [LocalProvider] Routing to {self.model} (Ollama)...")
            res = requests.post(
                self.base_url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=180
            )
            res.raise_for_status()
            return res.json().get("response", "")
        except Exception as e:
            print(f"  [LocalProvider] Error: {e}")
            return None

class IntentClassifier:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path(__file__).parent / "routing_config.json"
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"  [IntentClassifier] Error loading config: {e}. Using defaults.")
            self.config = {"levels": {}, "domains": {}, "default_level": "L2", "default_domain": "general"}

    def classify(self, prompt: str) -> dict:
        prompt_lower = prompt.lower()
        result = {
            "complexity": self.config.get("default_level", "L2"),
            "domain": self.config.get("default_domain", "general")
        }
        
        # 1. Domain Detection (Higher priority)
        for domain, d_config in self.config.get("domains", {}).items():
            for kw in d_config.get("keywords", []):
                if kw in prompt_lower:
                    result["domain"] = domain
                    break
            if result["domain"] == domain: break

        # 2. Complexity Detection
        # Check for L3 keywords
        l3_kws = self.config.get("levels", {}).get("L3", {}).get("keywords", [])
        if not l3_kws: # Fallback if config structure changed
             l3_kws = ["analyze", "design", "reason", "plan", "research", "audit", "deep dive"]
             
        for kw in l3_kws:
            if kw in prompt_lower:
                result["complexity"] = "L3"
                break
            
        # Check for L1 keywords
        l1_kws = self.config.get("levels", {}).get("L1", {}).get("keywords", [])
        if not l1_kws:
            l1_kws = ["translate", "summarize", "format", "fix", "clean"]

        if result["complexity"] != "L3":
            for kw in l1_kws:
                if kw in prompt_lower:
                    result["complexity"] = "L1"
                    break
        
        if len(prompt) > 2000: result["complexity"] = "L3"
        elif len(prompt) < 100: result["complexity"] = "L1"
        
        # 3. Thinking Depth Requirement
        l3_heavy = ["architecture", "optimize", "security", "complex", "strategy"]
        result["thinking_depth"] = "balanced"
        if result["complexity"] == "L3" or any(kw in prompt_lower for kw in l3_heavy):
            result["thinking_depth"] = "comprehensive"
        elif result["complexity"] == "L1":
            result["thinking_depth"] = "minimal"

        return result

class GroqProvider(LLMProvider):
    def __init__(self, api_key, model="llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def query(self, prompt: str) -> str:
        if not self.api_key: return None
        try:
            start = time.time()
            print(f"  [Groq] Routing to {self.model} (Requests Fallback)...")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            duration = time.time() - start
            print(f"  [Groq] OK ({duration:.2f}s)")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  [Groq] Error: {e}")
            return None

class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key, model="anthropic/claude-3.5-sonnet"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def query(self, prompt: str) -> str:
        if not self.api_key: return None
        try:
            print(f"  [OpenRouter] Routing to {self.model}...")
            res = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://antigravity.ai", # Optional
                    "X-Title": "Antigravity Assistant" 
                },
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
                timeout=30
            )
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  [OpenRouter] Error: {e}")
            return None

class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key, model="deepseek-coder"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.deepseek.com/chat/completions"

    def query(self, prompt: str) -> str:
        if not self.api_key: return None
        try:
            print(f"  [DeepSeek] Routing to {self.model}...")
            res = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": False},
                timeout=30
            )
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  [DeepSeek] Error: {e}")
            return None


class GeminiProvider(LLMProvider):
    def __init__(self, api_keys, model_name="gemini-3-flash-preview"):
        # Integrate KeyManager
        self.key_manager = KeyManager(api_keys, cooldown_seconds=60)
        self.model_name = model_name
        self.current_key = self.key_manager.get_key()
        self._setup_model(model_name)
        
        # Portkey Integration
        self.portkey_key = os.getenv("PORTKEY_API_KEY")
        if self.portkey_key:
            from portkey_ai import Portkey
            self.portkey = Portkey(api_key=self.portkey_key)
        else:
            self.portkey = None

    def _setup_model(self, model_name):
        if self.current_key:
            genai.configure(api_key=self.current_key)
            self.model = genai.GenerativeModel(model_name)

    def query(self, prompt: str, model_override=None) -> str:
        if not self.current_key: 
            # Try to get a key if we don't have one (maybe cooldown ended)
            self.current_key = self.key_manager.get_key()
            if not self.current_key:
                return None
                
        target_model_name = model_override if model_override else self.model_name
        
        # Start Trace for Observability
        trace_ctx = obs.start_trace(f"query_{int(time.time())}", f"llm_{target_model_name}")
        
        try:
            if self.portkey:
                # Route through Portkey Gateway (Semantic Cache & Unified Config)
                print(f"  [Portkey] Routing query via Gateway ({target_model_name})...")
                completion = self.portkey.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=target_model_name,
                    provider="google"
                )
                response_text = completion.choices[0].message.content
            else:
                # Direct Google SDK
                target_model = self.model
                if model_override and model_override != self.model_name:
                    target_model = genai.GenerativeModel(model_override)
                
                # Ensure we are using the current key
                genai.configure(api_key=self.current_key)
                
                response = target_model.generate_content(prompt, request_options={"timeout": 60})
                response_text = response.text

            obs.end_trace(trace_ctx, {"model": target_model_name, "status": "success"})
            return response_text
            
        except Exception as e:
            err_msg = str(e).lower()
            
            # Report error to KeyManager
            self.key_manager.report_error(self.current_key, err_msg)
            
            # If 429, rotate immediately and retry
            if "429" in err_msg or "quota" in err_msg:
                print(f"  [GeminiProvider] Rate limit hit. Rotating key...")
                obs.end_trace(trace_ctx, {"model": target_model_name, "status": "rate_limit"})
                
                if self._rotate_key():
                    return self.query(prompt, model_override)
                
                # If rotation fails (all keys exhausted), signal need for Local Fallback
                print(f"  [GeminiProvider] All Gemini keys exhausted. Triaging to local...")
                return "ERROR: ALL_KEYS_EXHAUSTED"
            
            # Other errors
            with open("llm_error.txt", "a") as f:
                import traceback
                f.write(f"\n--- Error with {target_model_name} ---\n")
                f.write(str(e) + "\n")
                f.write(traceback.format_exc() + "\n")
            
            print(f"  [GeminiProvider] Error with {target_model_name}: {e}.")
            obs.end_trace(trace_ctx, {"model": target_model_name, "status": "error", "error": str(e)})
            return None

    def get_embedding(self, text: str, model: str = "models/gemini-embedding-001") -> Optional[List[float]]:
        """Generates embeddings for the given text."""
        if not self.current_key:
            self.current_key = self.key_manager.get_key()
            if not self.current_key: return None
        
        try:
            genai.configure(api_key=self.current_key)
            result = genai.embed_content(
                model=model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"  [GeminiProvider] Embedding Error: {e}")
            return None

    def _rotate_key(self):
        new_key = self.key_manager.get_key()
        if new_key:
            self.current_key = new_key
            print(f"  [GeminiProvider] Switch to key: {self.current_key[:5]}...")
            self._setup_model(self.model_name)
            return True
        return False

class LLMManager:
    def __init__(self):
        self.providers = []
        self.classifier = IntentClassifier()
        self._setup_providers()

    def _setup_providers(self):
        # 1. Gemini (PRIMARY - Premium Brain from Google AI Pro)
        gemini_keys = os.getenv("GEMINI_API_KEY", "").split(",")
        if any(k.strip() for k in gemini_keys):
            print(f"  [LLMManager] Initializing GeminiProviders (PRIMARY)...")
            self.providers.append(GeminiProvider(gemini_keys, "models/gemini-3-pro-preview"))
            self.providers.append(GeminiProvider(gemini_keys, "models/gemini-3-flash-preview"))

        # 2. Groq (Fast Fallback)
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key: 
            print(f"  [LLMManager] Initializing GroqProvider (Fallback)...")
            self.providers.append(GroqProvider(groq_key))

        # 4. DeepSeek (fallback)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key: self.providers.append(DeepSeekProvider(deepseek_key))

        # 5. OpenRouter (fallback)
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key: self.providers.append(OpenRouterProvider(openrouter_key))

        # 6. Local Provider (Ollama - offline fallback)
        local_model = self.classifier.config.get("levels", {}).get("L1", {}).get("model", "phi3")
        self.providers.append(LocalProvider(model=local_model))

    def query(self, prompt: str, complexity: str = "auto", domain: str = "auto") -> str:
        """
        complexity: 'auto', 'L1' (local), 'L2' (flash), 'L3' (pro/reasoning)
        domain: 'auto', 'coding', 'reasoning', 'research', 'creative', 'general'
        """
        # 1. Classification
        if complexity == "auto" or domain == "auto":
            analysis = self.classifier.classify(prompt)
            if complexity == "auto": complexity = analysis["complexity"]
            if domain == "auto": domain = analysis["domain"]
            thinking_depth = analysis.get("thinking_depth", "balanced")
            print(f"  [Routing] Detected -> Complexity: {complexity}, Domain: {domain}, Thinking: {thinking_depth}")
        else:
            # Manual override or default from config
            config_depth = self.classifier.config.get("complexity_levels", {}).get(complexity, {}).get("default_thinking_depth", "balanced")
            thinking_depth = config_depth

        # 2. Expertise Selection
        model_override = None
        target_provider_type = None
        
        domain_config = self.classifier.config.get("domains", {}).get(domain, {})
        preferred_provider_name = domain_config.get("preferred_provider")
        preferred_model = domain_config.get("model")

        # Map Provider Name to Class
        provider_map = {
            "local": LocalProvider,
            "gemini": GeminiProvider,
            "groq": GroqProvider,
            "deepseek": DeepSeekProvider,
            "openrouter": OpenRouterProvider
        }
        
        target_provider_type = provider_map.get(preferred_provider_name)
        
        # Override for complexity L3 removed to allow Groq fallback
        pass

        # 3. 1st Pass: Try preferred expert
        if target_provider_type:
            for provider in self.providers:
                if isinstance(provider, target_provider_type):
                    # Handle specific provider arguments
                    if isinstance(provider, GeminiProvider):
                        res = provider.query(prompt, model_override=preferred_model or model_override)
                    elif isinstance(provider, (GroqProvider, OpenRouterProvider, DeepSeekProvider)):
                        # If a specific model is set in config for this domain, we'd need to support it
                        # For now, we use the default model configured in the provider instance
                        res = provider.query(prompt)
                    else:
                        res = provider.query(prompt)
                    
                    if res: return res

        # 4. 2nd Pass: Fallback Chain (Complexity based)
        print(f"  [Routing] Fallback triggered for {domain}/{complexity}")
        
        # Determine fallback order based on complexity
        if complexity == "L1":
            order = [GeminiProvider, GroqProvider, LocalProvider]
        elif complexity == "L3":
            order = [GeminiProvider, GroqProvider, OpenRouterProvider, LocalProvider]
            if not model_override:
                model_override = "models/gemini-3-pro-preview" # Default L3 model
        else:  # L2
            order = [GeminiProvider, GroqProvider, DeepSeekProvider, OpenRouterProvider, LocalProvider]

        for p_type in order:
            for provider in self.providers:
                if isinstance(provider, p_type):
                    # Add thinking instruction to prompt if not native
                    final_prompt = prompt
                    if thinking_depth == "comprehensive":
                        final_prompt = f"[THINKING: COMPREHENSIVE REASONING REQUIRED]\n{prompt}"
                    elif thinking_depth == "minimal":
                        final_prompt = f"[THINKING: FAST/MINIMAL]\n{prompt}"
                        
                    print(f"  [LLMManager] Trying provider: {type(provider).__name__} for depth {thinking_depth}...")
                    try:
                        res = provider.query(final_prompt, model_override=model_override) if isinstance(provider, GeminiProvider) else provider.query(final_prompt)
                        
                        if res == "ERROR: ALL_KEYS_EXHAUSTED":
                            print(f"  [LLMManager] Provider {type(provider).__name__} exhausted. Moving to next in chain.")
                            continue

                        if res: 
                            print(f"  [LLMManager] {type(provider).__name__} Success.")
                            return res
                    except Exception as e:
                        print(f"  [LLMManager] {type(provider).__name__} Failed: {e}")
                        continue

        print("  [LLMManager] ❌ All providers failed.")
        return None

    def embed(self, text: str) -> Optional[List[float]]:
        """Utility to get embeddings from the first available Gemini provider."""
        for provider in self.providers:
            if isinstance(provider, GeminiProvider):
                return provider.get_embedding(text)
        return None
