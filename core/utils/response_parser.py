import json
from core.utils.json_repair import repair_json
from core.utils.bot_logger import get_logger

logger = get_logger("response_parser")

def parse_json_response(response: str) -> dict:
    """
    Standardizes JSON extraction and repair from LLM responses.
    Handles markdown blocks and common malformations.
    """
    if not response:
        return {}

    try:
        # Try direct repair first
        repaired = repair_json(response)
        if isinstance(repaired, dict):
            return repaired
        
        # If repair_json failed or returned None, attempt manual cleanup
        cleaned = response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
            
        # Try parsing cleaned string
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Last ditch effort with repair_json on the cleaned bit
            final_attempt = repair_json(cleaned)
            return final_attempt if isinstance(final_attempt, dict) else {}

    except Exception as e:
        logger.error(f"Error parsing JSON response: {e}")
        return {}
