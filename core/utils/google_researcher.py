import os
import tempfile
from core.utils.drive_client import DriveClient
from core.utils.llm_manager import LLMManager

class GoogleResearcher:
    """
    Simulates NotebookLM functionality by grounding Gemini research in Google Drive data.
    """
    def __init__(self):
        self.drive = DriveClient()
        self.llm = LLMManager()

    def research_topic_in_drive(self, topic, folder_name=None):
        """
        Search for documents in Drive related to the topic and analyze them.
        """
        query = f"name contains '{topic}'"
        if folder_name:
             # Logic to find folder_id first could be added
             pass
        
        files = self.drive.list_files(query=query, max_results=5)
        if not files:
            return f"No documents found in Drive related to '{topic}'."

        context_data = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            for f in files:
                print(f"[*] Processing: {f['name']}")
                file_path = os.path.join(tmp_dir, f['name'])
                
                # Handle different mime types
                mime_type = f.get('mimeType', '')
                if mime_type == 'application/vnd.google-apps.folder':
                    print(f"[*] Skipping folder: {f['name']}")
                    continue
                elif mime_type in ['application/vnd.google-apps.document', 
                                 'application/vnd.google-apps.spreadsheet', 
                                 'application/vnd.google-apps.presentation']:
                    # Export to PDF for consistent reading
                    self.drive.export_google_doc(f['id'], file_path + ".pdf")
                    context_data.append(f"Document: {f['name']} (Google App Document)")
                elif 'google-apps' in mime_type:
                    print(f"[*] Skipping unsupported Google App file: {f['name']} ({mime_type})")
                    continue
                else:
                    self.drive.download_file(f['id'], file_path)
                    context_data.append(f"Document: {f['name']} (Downloaded)")

        research_prompt = f"""
        Deep Research Mode: Using the following found documents in Google Drive, analyze the topic: "{topic}"
        
        Found Documents:
        {chr(10).join(context_data)}
        
        Nhiệm vụ: 
        1. Tóm tắt các điểm chính từ các tài liệu tìm thấy.
        2. Kết nối chúng với kiến thức hiện có về {topic}.
        3. Nếu đây là dữ liệu giảng dạy, hãy đề xuất cấu trúc PACE-X 2.0.
        """
        
        return self.llm.query(research_prompt, complexity="L3")

if __name__ == "__main__":
    researcher = GoogleResearcher()
    # This will trigger OAuth if token_unified.json is missing
    print(researcher.research_topic_in_drive("Business Analysis"))
