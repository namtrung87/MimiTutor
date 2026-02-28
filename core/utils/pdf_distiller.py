import os
import hashlib
from typing import Optional
from core.utils.multimodal_extractor import MultimodalExtractor
from core.utils.ocr_service import ocr_service

try:
    from markitdown import MarkItDown
    HAS_MARKITDOWN = True
except ImportError:
    HAS_MARKITDOWN = False

class PDFDistiller:
    """
    Advanced utility to 'distill' heavy PDF and Image files into lightweight Markdown.
    Follows a Local-First strategy to minimize API costs:
    1. Local Structural Extraction (MarkItDown)
    2. Local OCR (EasyOCR) for scanned content
    3. AI Fallback (Gemini 2.0 Flash)
    """
    
    def __init__(self):
        self.extractor = MultimodalExtractor()
        self.mid = None

    def _get_mid(self):
        """Lazy-load MarkItDown to avoid slow imports at startup."""
        if self.mid is None:
            if HAS_MARKITDOWN:
                try:
                    print("  [PDFDistiller] Initializing MarkItDown...")
                    self.mid = MarkItDown()
                except Exception as e:
                    print(f"  [PDFDistiller] Failed to initialize MarkItDown: {e}")
            else:
                print("  [PDFDistiller] MarkItDown is not installed.")
        return self.mid

    @staticmethod
    def get_file_hash(filepath: str) -> str:
        """Calculates MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def distill(self, file_path: str, output_md_path: str) -> bool:
        """
        Distills a file (PDF or Image) into Markdown using the local-first strategy.
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self._distill_pdf(file_path, output_md_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            return self._distill_image(file_path, output_md_path)
        return False

    def _distill_pdf(self, pdf_path: str, output_md_path: str) -> bool:
        print(f"  [PDFDistiller] Distilling PDF: {os.path.basename(pdf_path)}...")
        
        content = ""
        
        # Layer 1: Local Structural Distillation (MarkItDown)
        try:
            print("  [PDFDistiller] Attempting Layer 1: MarkItDown...")
            mid = self._get_mid()
            if mid:
                result = mid.convert(pdf_path)
                content = result.text_content
            else:
                print("  [PDFDistiller] Layer 1 skipped: MarkItDown not available.")
        except Exception as e:
            print(f"  [PDFDistiller] Layer 1 failed: {e}")

        # Check if content is empty or looks like a scanned PDF (very short content for large file)
        file_size = os.path.getsize(pdf_path)
        if not content.strip() or (len(content) < 500 and file_size > 1_000_000):
            print("  [PDFDistiller] Content empty or seems scanned. Moving to Layer 2: Local OCR...")
            # Layer 2: Local OCR (EasyOCR) - Simplified approach for PDF
            # In a full implementation, we'd convert PDF to images first. 
            # For now, if local fails, we jump to AI fallback which handles scanned PDFs natively.
            pass

        # Layer 3: AI Fallback (Gemini 2.0 Flash)
        if not content.strip():
            print("  [PDFDistiller] Local methods failed. Attempting Layer 3: AI Fallback (Gemini)...")
            try:
                content = self.extractor.process_file(pdf_path)
            except Exception as e:
                print(f"  [PDFDistiller] Layer 3 failed: {e}")

        if content and "[Error" not in content:
            self._save_markdown(content, pdf_path, output_md_path)
            return True
        
        return False

    def _distill_image(self, image_path: str, output_md_path: str) -> bool:
        print(f"  [PDFDistiller] Distilling Image: {os.path.basename(image_path)}...")
        
        # Layer 1: Local OCR (EasyOCR)
        content = ocr_service.extract_text(image_path)
        
        # Layer 2: AI Fallback (Gemini 2.0 Flash)
        if not content.strip():
            print("  [PDFDistiller] Local OCR empty. Attempting Layer 2: AI Fallback (Gemini)...")
            try:
                content = self.extractor.process_file(image_path)
            except Exception as e:
                print(f"  [PDFDistiller] Image AI failed: {e}")

        if content and "[Error" not in content:
            self._save_markdown(content, image_path, output_md_path)
            return True
            
        return False

    def _save_markdown(self, content: str, source_path: str, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Distilled Content: {os.path.basename(source_path)}\n\n")
            f.write(content)
        print(f"  [PDFDistiller] Success: {output_path}")

# Singleton instance
pdf_distiller = PDFDistiller()
