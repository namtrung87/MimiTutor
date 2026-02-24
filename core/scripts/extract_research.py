import os
import json

folder = r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\research_results\Pain point for gamifications"
output_folder = r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\research_results\extracted"
os.makedirs(output_folder, exist_ok=True)

results = {}

for filename in os.listdir(folder):
    filepath = os.path.join(folder, filename)
    text = ""
    cert_name = filename.replace("_Pain_Point_Topics_Analysis", "").replace("_Certification_Pain_Point_Analysis", "").replace("_Pain_Point_Analysis", "")
    cert_name = os.path.splitext(cert_name)[0]
    
    try:
        if filename.endswith(".pdf"):
            import pypdf
            with open(filepath, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif filename.endswith(".docx"):
            try:
                import docx
                doc = docx.Document(filepath)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            except ImportError:
                print(f"python-docx not installed, trying alternative for {filename}")
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(filepath) as z:
                    with z.open('word/document.xml') as xml_file:
                        tree = ET.parse(xml_file)
                        root = tree.getroot()
                        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                        for para in root.findall('.//w:p', ns):
                            texts = [t.text for t in para.findall('.//w:t', ns) if t.text]
                            if texts:
                                text += ''.join(texts) + "\n"
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        continue
    
    if text.strip():
        txt_path = os.path.join(output_folder, f"{cert_name}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        results[cert_name] = len(text)
        print(f"[+] Extracted {cert_name}: {len(text)} chars")
    else:
        print(f"[-] No text extracted from {filename}")

print(f"\n--- Extraction Complete: {len(results)} files ---")
for name, chars in results.items():
    print(f"  {name}: {chars:,} characters")
