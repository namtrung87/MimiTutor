import os
from docx import Document

source_dir = r"c:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\research_results\Pain point for gamifications"
target_dir = r"c:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\research_results\extracted\mgmt_accounting_research"

if not os.path.exists(target_dir):
    os.makedirs(target_dir)

for filename in os.listdir(source_dir):
    if filename.endswith(".docx"):
        doc_path = os.path.join(source_dir, filename)
        try:
            doc = Document(doc_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            
            txt_filename = filename.replace(".docx", ".txt")
            txt_path = os.path.join(target_dir, txt_filename)
            
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(full_text))
            print(f"Extracted: {filename}")
        except Exception as e:
            print(f"Error extracting {filename}: {e}")
