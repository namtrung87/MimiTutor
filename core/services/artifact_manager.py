import os
import json
from datetime import datetime

class ArtifactManager:
    """
    Manages long-term persistent artifacts (checklists, plans, reports)
    to provide agents with a shared, externalized memory space.
    """
    def __init__(self, workspace_path="data/artifacts"):
        self.workspace_path = workspace_path
        if not os.path.exists(self.workspace_path):
            os.makedirs(self.workspace_path)

    def create_artifact(self, name: str, content: str, artifact_type: str = "task"):
        """Creates or overwrites an artifact file."""
        filename = f"{name}.md"
        path = os.path.join(self.workspace_path, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Artifact: {name}\n")
            f.write(f"Type: {artifact_type}\n")
            f.write(f"Created: {datetime.now().isoformat()}\n")
            f.write("---\n\n")
            f.write(content)
        
        return path

    def update_artifact(self, name: str, new_content: str):
        """Appends or updates an existing artifact."""
        path = os.path.join(self.workspace_path, f"{name}.md")
        if not os.path.exists(path):
            return self.create_artifact(name, new_content)
        
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n\n## Update: {datetime.now().isoformat()}\n")
            f.write(new_content)
        
        return path

    def list_artifacts(self):
        """Lists all managed artifacts."""
        return [f.replace(".md", "") for f in os.listdir(self.workspace_path) if f.endswith(".md")]

    def read_artifact(self, name: str):
        """Reads artifact content."""
        path = os.path.join(self.workspace_path, f"{name}.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return None

# Global instance
artifact_manager = ArtifactManager()
