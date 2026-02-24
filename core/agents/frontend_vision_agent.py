import google.generativeai as genai
import os
import mimetypes
from core.utils.llm_manager import KeyManager
from core.state import AgentState

class FrontendVisionAgent:
    """
    OAC (Orchesta App Creator) Vision Agent.
    Transforms UI sketches, wireframes, or descriptions into premium React Native code.
    """
    def __init__(self):
        gemini_keys_env = os.environ.get("GEMINI_API_KEY", "")
        self.key_manager = KeyManager(gemini_keys_env.split(","))

    def generate_screen(self, image_path: str, additional_context: str = "") -> str:
        """
        Analyzes an image and returns a complete React Native screen file content.
        """
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith("image/"):
            return "Error: Valid image file required for Vision Agent."

        try:
            genai.configure(api_key=self.key_manager.get_working_key())
            uploaded_file = genai.upload_file(path=image_path, mime_type=mime_type)
            
            # Using 1.5 Pro or Flash for Vision. 2.0 Flash is even better.
            model = genai.GenerativeModel("gemini-3-flash-preview")
            
            prompt = f"""
            You are the Orchesta App Creator (OAC) specialized in iPhone development.
            
            MISSION:
            Convert this UI sketch/image into a premium React Native screen component.
            
            CONSTRAINTS:
            1. Use 'orchesta-mobile/src/theme.js' for all colors, spacing, and radius tokens.
            2. Implement 'glassmorphism' using the 'styles.glass' preset from theme.js.
            3. Use 'react-native-linear-gradient' for background gradients if applicable.
            4. Use 'lucide-react-native' for icons.
            5. Ensure the design looks "Premium" and "Apple-like" (vibrant colors, clean typography, generous spacing).
            6. Return ONLY the code for a complete .js file.
            
            ADDITIONAL CONTEXT FROM USER: {additional_context}
            
            Strictly follow the 'Intent-First' OAC protocol.
            """

            response = model.generate_content([uploaded_file, prompt])
            
            # Clean up
            try:
                genai.delete_file(uploaded_file.name)
            except:
                pass
                
            return response.text
        except Exception as e:
            return f"Error in FrontendVisionAgent: {str(e)}"

def vision_node(state: AgentState):
    """Integrated node for the agent graph to handle mobile vision requests."""
    # This would be used if OAC is triggered in a graph flow
    pass
