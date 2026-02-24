import google.generativeai as genai
import os
import mimetypes
from core.utils.llm_manager import KeyManager

class MultimodalExtractor:
    def __init__(self):
        gemini_keys_env = os.environ.get("GEMINI_API_KEY", "")
        self.key_manager = KeyManager(gemini_keys_env.split(","))

    def process_file(self, file_path: str, mime_type: str = None) -> str:
        """
        Extracts text from an audio or image file.
        Returns the transcribed text or image description.
        """
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
            
        if not mime_type:
            return "[File format not recognized]"
            
        try:
            # Ensure key is configured
            genai.configure(api_key=self.key_manager.get_working_key())
            
            # Upload file to Gemini API
            print(f"  [Multimodal] Uploading {file_path} (MIME: {mime_type})")
            uploaded_file = genai.upload_file(path=file_path, mime_type=mime_type)
            
            model = genai.GenerativeModel("gemini-3-flash-preview")
            
            if mime_type.startswith("audio/"):
                prompt = "Please transcribe this audio exactly as spoken in Vietnamese. If an exercise is read, transcribe the full exercise text."
            elif mime_type.startswith("image/"):
                prompt = "Please extract the text and describe any equations or diagrams from this image. It is an exercise/homework image in Vietnamese."
            else:
                prompt = "Please describe the contents of this file."

            response = model.generate_content([uploaded_file, prompt])
            
            # Clean up the file from Google's servers
            try:
                genai.delete_file(uploaded_file.name)
            except Exception as e:
                print(f"  [Multimodal] Warning: failed to delete temp file {uploaded_file.name}: {e}")
            
            return response.text
        except Exception as e:
            print(f"  [Multimodal] Error extracting content: {e}")
            return f"[Error processing file: {str(e)}]"
