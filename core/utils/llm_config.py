import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

class LLMConfigManager:
    """
    Manages persistent LLM service toggles for different applications.
    Loads config from a JSON file and merges with baseline defaults.
    """
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        if config_path is None:
            # Robustly find the central data/llm_config.json
            # We look for the 'Orchesta assistant' directory which is the root
            current_file = Path(__file__).resolve()
            root_dir = None
            for parent in current_file.parents:
                if (parent / "BRAIN.md").exists() or (parent / "HEARTBEAT.md").exists():
                    root_dir = parent
                    break
            
            if not root_dir:
                # Fallback to local data dir if root not found
                root_dir = current_file.parents[2]
                
            data_dir = root_dir / "data"
            data_dir.mkdir(exist_ok=True)
            config_path = str(data_dir / "llm_config.json")
            
        self.config_path = config_path
        self.defaults = {
            "command_center": {
                "gemini": True,
                "groq": True,
                "9router": False,
                "openrouter": True,
                "local": True,
                "cerebras": True,
                "sambanova": False,
                "mistral": False
            },
            "mimi_hometutor": {
                "gemini": True,
                "groq": True,
                "9router": False,
                "openrouter": True,
                "local": True,
                "cerebras": True,
                "sambanova": False,
                "mistral": False
            },
            "telegram_bot": {
                "gemini": True,
                "groq": True,
                "9router": False,
                "openrouter": True,
                "local": True,
                "cerebras": True,
                "sambanova": False,
                "mistral": False
            }
        }
        self.config = self._load()

    def _load(self) -> Dict[str, Dict[str, bool]]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                    # Merge apps
                    merged = self.defaults.copy()
                    for app, settings in stored.items():
                        if app in merged:
                            merged[app].update(settings)
                        else:
                            merged[app] = settings
                    return merged
            except (json.JSONDecodeError, IOError):
                return self.defaults.copy()
        return self.defaults.copy()

    def _save(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving LLM configuration: {e}")

    def is_enabled(self, app_name: str, provider_id: str) -> bool:
        """Checks if a specific provider is enabled for an app."""
        app_settings = self.config.get(app_name, self.defaults.get(app_name, {}))
        return app_settings.get(provider_id, True)

    def set_provider_status(self, app_name: str, provider_id: str, enabled: bool) -> None:
        """Sets a provider state and persists it."""
        if app_name not in self.config:
            self.config[app_name] = {}
        self.config[app_name][provider_id] = enabled
        self._save()

    def get_all(self) -> Dict[str, Dict[str, bool]]:
        """Returns all current configurations."""
        return self.config

# Singleton instance for system-wide use
llm_config = LLMConfigManager()
