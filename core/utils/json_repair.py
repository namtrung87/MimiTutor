import json
import re
import ast

def repair_json(json_str: str) -> dict:
    """
    Attempts to repair and parse a JSON string that might be malformed
    (e.g., contains markdown, trailing commas, or Python-style booleans).
    """
    if not json_str:
        return None

    # 1. Strip Markdown Code Blocks
    # Matches ```json ... ``` or just ``` ... ```
    if "```" in json_str:
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, json_str)
        if match:
            json_str = match.group(1)

    # 2. Extract JSON object (find outer brackets)
    start = json_str.find("{")
    end = json_str.rfind("}")
    if start != -1 and end != -1:
        json_str = json_str[start:end+1]
    else:
        # If no brackets found, it's not a valid object
        return None

    # 3. Attempt Standard Parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 4. Common Fixes for 'Almost Valid' JSON
    # Fix trailing commas: ,} -> } and ,] -> ]
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    
    # Fix Python booleans/None: True -> true, False -> false, None -> null
    # (Be careful not to replace inside strings, but for simple structural JSON this is usually fine)
    # A safer way is to use ast.literal_eval if it looks like a Python dict
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 5. Last Resort: AST Evaluation (for Python-dict style output)
    try:
        # This handles True, False, None, and single quotes key='value'
        data = ast.literal_eval(json_str)
        if isinstance(data, dict):
            return data
    except (ValueError, SyntaxError):
        pass

    return None
