import os
import json
from typing import Dict, Any, Optional

class FeatureFlags:
    """
    Manages persistent feature toggles for the Orchesta system.
    This class loads flags from a JSON configuration file and merges them with default values.
    """
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initializes the FeatureFlags manager.
        
        Args:
            config_path (Optional[str]): Absolute path to the feature flags JSON file.
                                         Defaults to data/feature_flags.json if not provided.
        """
        if config_path is None:
            # Default to data/feature_flags.json relative to project root
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            config_path = os.path.join(data_dir, "feature_flags.json")
            
        self.config_path = config_path
        self.defaults = {
            "telegram_bot": True,
            "dashboard_api": True,
            "scheduler": True,
            "watchdog": True,
            "night_shift": True,
            "morning_sync": True,
            "evening_wrapup": True,
            "commute_mode": False,
            "growth_pipeline": True,
            "api_unlocked_night": False
        }
        self.flags = self._load()

    def _load(self) -> Dict[str, bool]:
        """
        Loads flags from disk, merging with defaults.
        
        Returns:
            Dict[str, bool]: A dictionary of all current feature flags.
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                    # Merge stored with defaults to ensure all keys exist
                    return {**self.defaults, **stored}
            except (json.JSONDecodeError, IOError):
                return self.defaults.copy()
        return self.defaults.copy()

    def _save(self) -> None:
        """
        Persists current flags to disk.
        Silently catches IOErrors and prints them to avoid crashing the system.
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.flags, f, indent=4)
        except IOError as e:
            print(f"Error saving feature flags: {e}")

    def is_enabled(self, feature: str) -> bool:
        """
        Checks if a specific feature is enabled.
        
        Args:
            feature (str): The name of the feature to check.
            
        Returns:
            bool: True if the feature is enabled (or defaults to True), False otherwise.
        """
        return self.flags.get(feature, self.defaults.get(feature, False))

    def set_feature(self, feature: str, enabled: bool) -> None:
        """
        Sets a feature state and persists it to the configuration file.
        
        Args:
            feature (str): The name of the feature to update.
            enabled (bool): The new boolean state for the feature.
        """
        self.flags[feature] = enabled
        self._save()

    def get_all(self) -> Dict[str, bool]:
        """Returns all current feature flags."""
        return self.flags.copy()

# Singleton instance
feature_flags = FeatureFlags()
