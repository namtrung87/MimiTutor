import os
import mimetypes
import uuid
from typing import List, Dict, Any, Optional
from google import genai
from core.utils.llm_manager import KeyManager, UsageStats

class MultimodalExtractor:
    def __init__(self):
        gemini_keys_env = os.environ.get("GEMINI_API_KEY", "")
        self.key_manager = KeyManager(gemini_keys_env.split(","))

    def process_file(self, file_path: str, mime_type: Optional[str] = None) -> str:
        """
        Extracts text and context from an audio, image, or document file.
        Returns the transcribed text, image description, or document summary.
        """
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
            
        if not mime_type:
            # Fallback for voice notes which are often .oga
            if file_path.endswith('.oga'):
                mime_type = 'audio/ogg'
            else:
                return "[File format not recognized]"
            
        try:
            # Initialize new genai client
            client = genai.Client(api_key=self.key_manager.get_key())
            
            # Upload file to Gemini API
            print(f"  [Multimodal] Uploading {file_path} (MIME: {mime_type})")
            
            # Fix for non-ASCII filenames which cause upload errors on some systems
            import shutil
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"ext_temp_{str(uuid.uuid4())[:8]}{os.path.splitext(file_path)[1]}")
            shutil.copy2(file_path, temp_file_path)
            
            try:
                uploaded_file = client.files.upload(file=temp_file_path, config={'mime_type': mime_type})
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
            # Using Gemini 2.0 Flash (Optimized for speed and much lower cost)
            model_id = "gemini-2.0-flash"
            
            if mime_type.startswith("audio/"):
                prompt = "You are a helpful assistant. Please transcribe everything spoken in this audio exactly, in Vietnamese. If the user gives an instruction or command, extract it clearly."
            elif mime_type.startswith("image/"):
                prompt = "Please extract all text and describe any content, equations, or diagrams from this image in Vietnamese."
            else:
                prompt = "Please read this document carefully and provide a comprehensive summary and any key action items or data points found within, in Vietnamese."

            print(f"  [Multimodal] Generating content with {model_id}...")
            
            # Route through LLMManager for tracking/fallback
            from core.llm import LLMManager
            llm = LLMManager(app_name="multimodal_extractor")
            
            # NOTE: We keep genai.Client for the upload and generate_content because LiteLLM's 
            # support for Gemini-native file-upload objects is complex. 
            # However, we ensure usage is tracked via the existing UsageStats calls.
            response = client.models.generate_content(
                model=model_id,
                contents=[uploaded_file, prompt]
            )
            
            # Log usage
            try:
                usage = response.usage_metadata
                UsageStats.log_usage(
                    model_id, 
                    usage.prompt_token_count, 
                    usage.candidates_token_count
                )
            except Exception as usage_err:
                print(f"  [Multimodal] Warning: Failed to log usage: {usage_err}")
            
            # Clean up the file from Google's servers
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as e:
                print(f"  [Multimodal] Warning: failed to delete temp file {uploaded_file.name}: {e}")
            
            return response.text
        except Exception as e:
            print(f"  [Multimodal] Error extracting content: {e}")
            return f"[Error processing file: {str(e)}]"
