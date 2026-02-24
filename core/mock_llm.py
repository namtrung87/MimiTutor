import json
import time
from core.utils.z_research import ZResearch

class MockLLM:
    """
    A previously mock LLM, now powered by Z.ai (Zhibu AI) for real agentic tasks.
    """
    def __init__(self):
        self.researcher = ZResearch()

    def extract_skill(self, file_content: str) -> dict:
        """
        Analyze code and extract a skill using Z.ai Agent Mode.
        """
        print("  [Z.ai] Analyzing file content for skill extraction...")
        
        prompt = f"""
        Analyze the following code content and extract a 'skill' definition. 
        Return a JSON object with the following fields:
        - title: A concise name for the skill.
        - description: A short description of what the code does.
        - logic_summary: A detailed summary of the main logic.
        - dependencies: A list of libraries or modules this code depends on.

        Code content:
        {file_content}

        Respond ONLY with the JSON object.
        """
        
        response = self.researcher.query(prompt, complexity="reasoning")
        
        try:
            # Attempt to parse JSON from the response
            # Sometimes models include markdown blocks
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:-3].strip()
            elif clean_response.startswith("```"):
                clean_response = clean_response[3:-3].strip()
            
            return json.loads(clean_response)
        except Exception as e:
            print(f"  [Z.ai] Error parsing JSON response: {e}. Falling back to default.")
            return {
                "title": "Extracted Skill",
                "description": "Analysis performed by Z.ai.",
                "logic_summary": response[:5000],
                "dependencies": []
            }
