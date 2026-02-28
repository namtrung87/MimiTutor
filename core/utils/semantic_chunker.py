import re
from typing import List

class SemanticChunker:
    """
    Splits text into chunks based on semantic boundaries like headers, 
    paragraphs, and sentence endings rather than fixed character counts.
    """
    
    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        """
        Main method to split text into semantic chunks.
        """
        # 1. Try splitting by Markdown Headers first if present
        if "# " in text:
            return self._split_by_headers(text)
        
        # 2. Fallback to paragraph and sentence splitting
        return self._split_by_structure(text)

    def _split_by_headers(self, text: str) -> List[str]:
        # Split by any level of header (#, ##, ###, etc.)
        sections = re.split(r'(\n#{1,6}\s+.*)', text)
        
        chunks = []
        current_chunk = ""
        
        for section in sections:
            if not section.strip():
                continue
                
            if len(current_chunk) + len(section) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If a single section is too big, split it by structure
                if len(section) > self.chunk_size:
                    sub_chunks = self._split_by_structure(section)
                    chunks.extend(sub_chunks[:-1]) # add all but last
                    current_chunk = sub_chunks[-1] # keep last as base for next
                else:
                    current_chunk = section
            else:
                current_chunk += section
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def _split_by_structure(self, text: str) -> List[str]:
        # Split by double newline (paragraphs)
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = ""
        
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
                
            if len(current_chunk) + len(p) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If a paragraph is still too big, split by sentences
                if len(p) > self.chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', p)
                    for s in sentences:
                        if len(current_chunk) + len(s) > self.chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = s
                        else:
                            current_chunk += " " + s if current_chunk else s
                else:
                    current_chunk = p
            else:
                current_chunk += "\n\n" + p if current_chunk else p
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
