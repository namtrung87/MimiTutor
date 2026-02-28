import os
from typing import Optional

class SecurityGuard:
    """
    Enforces Zero-Touch security protocols.
    Prevents agents from accessing files outside the approved workspace.
    """
    def __init__(self, workspace_root: Optional[str] = None):
        # Approved roots for the security guard
        self.approved_roots = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Mimi learning"))
        ]
        
        print(f"  [Security] Scoped to: {self.approved_roots}")

    def is_path_safe(self, target_path: str) -> bool:
        """Checks if a path is inside any of the approved roots."""
        absolute_target = os.path.abspath(target_path)
        return any(absolute_target.startswith(root) for root in self.approved_roots)

    def secure_open(self, file_path: str, mode: str = 'r', **kwargs):
        """Opens a file only if it is within the workspace root."""
        if not self.is_path_safe(file_path):
            raise PermissionError(f"Security Alert: Attempted access to file outside workspace: {file_path}")
        return open(file_path, mode, **kwargs)

    def secure_list_dir(self, directory_path: str):
        """Lists a directory only if it is within the workspace root."""
        if not self.is_path_safe(directory_path):
            raise PermissionError(f"Security Alert: Attempted listing of directory outside workspace: {directory_path}")
        return os.listdir(directory_path)

# Global instances
security_guard = SecurityGuard()
