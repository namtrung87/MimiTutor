import docx
import os

def extract_text(docx_path, output_path):
    if not os.path.exists(docx_path):
        print(f"Error: {docx_path} not found.")
        return
    
    doc = docx.Document(docx_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(full_text))
    print(f"Successfully extracted text to {output_path}")

if __name__ == "__main__":
    docx_path = r"C:\Users\Trung Nguyen\Desktop\Working data\Chương 3- Thiết kế nghiên cứu và kết quả thực nghiệm.docx"
    output_path = r"chapter3_content.txt"
    extract_text(docx_path, output_path)
