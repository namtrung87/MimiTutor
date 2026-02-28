import os
import subprocess
import tempfile
from core.utils.drive_client import DriveClient

class ColabAutomator:
    """
    Automates Google Colab execution by pulling notebooks from Drive and running them locally.
    """
    def __init__(self):
        self.drive = DriveClient()

    def run_notebook_from_drive(self, notebook_name):
        """
        Finds a notebook in Drive, downloads it, converts to .py, and runs it.
        """
        files = self.drive.list_files(query=f"name = '{notebook_name}' and mimeType = 'application/x-ipynb+json'", max_results=1)
        if not files:
            return f"Notebook '{notebook_name}' not found in Drive."

        file_id = files[0]['id']
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            ipynb_path = os.path.join(tmp_dir, notebook_name)
            py_path = ipynb_path.replace(".ipynb", ".py")
            
            print(f"[*] Downloading notebook: {notebook_name}")
            self.drive.download_file(file_id, ipynb_path)
            
            # Convert to .py
            print(f"[*] Converting to Python script...")
            try:
                subprocess.run([
                    "python", "-m", "jupyter", "nbconvert", 
                    "--to", "script", 
                    ipynb_path, 
                    "--output-dir", tmp_dir
                ], check=True)
            except Exception as e:
                return f"Failed to convert notebook: {e}. Ensure 'nbconvert' is installed."

            # Run the script
            print(f"[*] Executing script...")
            try:
                result = subprocess.run(["python", py_path], capture_output=True, text=True)
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0
                }
            except Exception as e:
                return f"Execution failed: {e}"

if __name__ == "__main__":
    automator = ColabAutomator()
    # Example usage (test)
    # result = automator.run_notebook_from_drive("MyTestColab.ipynb")
    # print(result)
    print("ColabAutomator initialized.")
