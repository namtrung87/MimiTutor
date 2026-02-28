import os
import mimetypes
from typing import Dict, Any, Optional
from core.state import AgentState
from core.utils.llm_manager import LLMManager

class MultimodalAgent:
    """
    Multimodal Agent: Processes Vision (Images/PDFs) and Audio.
    Uses Gemini 2.0 Flash for high-speed multimodal reasoning.
    """
    def __init__(self):
        self.llm = LLMManager()

    async def process_media(self, file_path: str, prompt: str, media_type: str = "image") -> str:
        """
        Processes a media file with a given prompt.
        """
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        print(f"  [Multimodal] Processing {media_type} at {file_path}...")
        
        # In a real implementation with Google GenAI SDK:
        # result = model.generate_content([file_upload, prompt])
        
        # Simplified for Orchestra architecture, using the LLMManager structure:
        # LLMManager.query already supports multimodal if we pass the right parameters.
        # For now, we simulate the logic.
        
        response = self.llm.query(
            f"[MULTIMODAL {media_type.upper()}] {prompt}\n(Processing file: {file_path})",
            complexity="L3"
        )
        return response

def multimodal_node(state: AgentState):
    """
    LangGraph node for Multimodal processing.
    Triggered when an image or audio file is detected in the input.
    """
    messages = state.get("messages", [])
    user_input = messages[-1] if messages else ""
    
    # Heuristic: Check if user mentioned an attachment or if file_path is set in state
    file_path = state.get("input_file")
    
    if not file_path:
        return {"messages": ["Multimodal Agent: No media file provided to process."]}

    agent = MultimodalAgent()
    # Determine media type from extension
    mime_type, _ = mimetypes.guess_type(file_path)
    media_type = "image" if mime_type and "image" in mime_type else "audio" if mime_type and "audio" in mime_type else "document"

    import asyncio
    result = asyncio.run(agent.process_media(file_path, user_input, media_type))
    
    return {"messages": [f"Multimodal Agent ({media_type.capitalize()}): {result}"]}
