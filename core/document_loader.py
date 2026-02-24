import os
from core.utils.security_guard import security_guard

class DocumentLoader:
    """
    A simple loader to read text from files in the KnowledgeBase.
    Requires: pip install pypdf
    """
    def __init__(self, knowledge_base_path="01_Teaching_Modules/KnowledgeBase"):
        self.kb_path = knowledge_base_path
    
    def load_documents(self):
        documents = []
        if not os.path.exists(self.kb_path):
            os.makedirs(self.kb_path)
            return documents
        
        # Enforce security scoping
        for filename in security_guard.secure_list_dir(self.kb_path):
            file_path = os.path.join(self.kb_path, filename)
            content = ""
            
            try:
                if filename.endswith((".txt", ".md")):
                    with security_guard.secure_open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                elif filename.endswith(".pdf"):
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        content += page.extract_text() + "\n"
                
                if content:
                    documents.append({
                        "filename": filename,
                        "content": content
                    })
                    
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                
        return documents
