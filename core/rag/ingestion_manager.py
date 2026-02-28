import os
import hashlib
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Late imports to avoid issues while package installs
# from docling.document_converter import DocumentConverter

class IngestionManager:
    """
    Manages the ingestion pipeline for a 2026-style RAG stack.
    Includes Docling parsing, incremental processing via hashing, and hierarchical chunking.
    """
    def __init__(self, metadata_path: str = "data/rag_metadata.json"):
        self.metadata_path = Path(metadata_path)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata = self._load_metadata()
        self.converter = None # Lazy load docling

    def _load_metadata(self) -> Dict[str, Any]:
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"files": {}}

    def _save_metadata(self):
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)

    def _get_file_hash(self, file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def process_file(self, file_path: str, force: bool = False) -> Optional[Dict[str, Any]]:
        file_path = str(Path(file_path).absolute())
        file_hash = self._get_file_hash(file_path)

        if not force and file_path in self.metadata["files"]:
            if self.metadata["files"][file_path]["hash"] == file_hash:
                print(f"Skipping {os.path.basename(file_path)} (unchanged)")
                return None

        print(f"Parsing {os.path.basename(file_path)} with Docling...")
        markdown_content = self._parse_with_docling(file_path)
        
        # Hierarchical Chunking
        chunks = self.chunk_hierarchically(markdown_content)
        
        result = {
            "path": file_path,
            "hash": file_hash,
            "last_processed": time.time(),
            "chunk_count": len(chunks),
            "content_preview": markdown_content[:200]
        }
        
        self.metadata["files"][file_path] = result
        self._save_metadata()
        
        return {**result, "chunks": chunks, "full_content": markdown_content}

    def _parse_with_docling(self, file_path: str) -> str:
        try:
            from docling.document_converter import DocumentConverter
            if self.converter is None:
                self.converter = DocumentConverter()
            
            result = self.converter.convert(file_path)
            return result.document.export_to_markdown()
        except ImportError:
            print("WARNING: docling not installed correctly. Falling back to basic text read.")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"Error parsing with Docling: {e}")
            return ""

    def chunk_hierarchically(self, text: str) -> List[Dict[str, Any]]:
        """
        Implements hierarchical chunking:
        1. Sections (split by headers)
        2. Semantic/Fixed chunks within sections
        """
        # Simple implementation for now: Split by markdown headers
        lines = text.split('\n')
        sections = []
        current_section = {"title": "Introduction", "content": []}
        
        for line in lines:
            if line.startswith('#'):
                if current_section["content"]:
                    sections.append({
                        "title": current_section["title"],
                        "content": '\n'.join(current_section["content"])
                    })
                current_section = {"title": line.strip('# '), "content": []}
            else:
                current_section["content"].append(line)
        
        if current_section["content"]:
            sections.append({
                "title": current_section["title"],
                "content": '\n'.join(current_section["content"])
            })

        # Further subdivide long sections into 1000-char chunks
        final_chunks = []
        for sec in sections:
            content = sec["content"]
            if len(content) > 1000:
                for i in range(0, len(content), 800): # Overlap of 200
                    chunk_text = content[i:i+1000]
                    final_chunks.append({
                        "parent_title": sec["title"],
                        "text": chunk_text,
                        "type": "semantic"
                    })
            else:
                final_chunks.append({
                    "parent_title": sec["title"],
                    "text": content,
                    "type": "section_summary" if len(content) < 200 else "semantic"
                })
        
        return final_chunks

if __name__ == "__main__":
    # Test
    manager = IngestionManager()
    # test_file = "BRAIN.md"
    # res = manager.process_file(test_file)
    # print(res)
