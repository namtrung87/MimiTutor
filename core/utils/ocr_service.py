try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

import os
import logging
from typing import List, Optional

logger = logging.getLogger("orchesta.ocr")

class OCRService:
    """
    Local OCR Service using EasyOCR.
    Provides cost-free text extraction from images and scanned PDF pages.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCRService, cls).__new__(cls)
            cls._instance.reader = None
        return cls._instance

    def _get_reader(self):
        """Lazy-load the EasyOCR reader."""
        if self.reader is None:
            if not HAS_EASYOCR:
                logger.error("EasyOCR is not installed. OCR functionality will be disabled.")
                return None
            try:
                logger.info("Initializing EasyOCR reader (VI, EN)...")
                self.reader = easyocr.Reader(['vi', 'en'], gpu=False)
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")
                return None
        return self.reader

    def extract_text(self, image_path: str) -> str:
        """
        Extracts text from an image file using EasyOCR.
        """
        if not os.path.exists(image_path):
            return ""
            
        reader = self._get_reader()
        if not reader:
            return "[OCR Error: easyocr not available]"

        logger.info(f"Running OCR on {os.path.basename(image_path)}...")
        try:
            results = reader.readtext(image_path, detail=0)
            return "\n".join(results)
        except Exception as e:
            logger.error(f"Error during OCR: {e}")
            return ""

# Singleton instance
ocr_service = OCRService()
