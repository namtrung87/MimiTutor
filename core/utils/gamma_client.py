import requests
import json
import os

class GammaClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GAMMA_API_KEY")
        if not self.api_key:
            print("[!] Warning: GAMMA_API_KEY not found in parameters or .env")
        self.base_url = "https://public-api.gamma.app/v1.0"
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

    def generate_presentation(self, input_text, text_mode="preserve"):
        """
        text_mode options: 'generate', 'condense', 'preserve'
        """
        url = f"{self.base_url}/generations"
        payload = {
            "inputText": input_text,
            "textMode": text_mode,
            "format": "presentation"
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Gamma API Error {response.status_code}: {response.text}")

    def get_generation_status(self, generation_id):
        """
        Retrieves status and final URL for a generation.
        """
        url = f"{self.base_url}/generations/{generation_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Gamma Status API Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    # Quick connectivity test
    KEY = "sk-gamma-ASknHVq1Fru13LfngB330gmXEWSiA5sWqxvSgTPLw"
    client = GammaClient(KEY)
    print("Gamma Client initialized.")
