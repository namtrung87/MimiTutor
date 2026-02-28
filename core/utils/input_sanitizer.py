import re

def sanitize_user_input(text: str, max_length: int = 2000) -> str:
    """
    Strips control characters, limits length, and escapes potential prompt injection patterns.
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Limit length
    text = text[:max_length]

    # 2. Strip control characters (except common whitespace like \n, \t)
    # This keeps unicode characters but removes low-level control chars
    text = "".join(ch for ch in text if ord(ch) >= 32 or ch in "\n\r\t")

    # 3. Escape common prompt injection / command markers
    # We don't want to break legitimate usage, so we mainly focus on preventing 
    # the agent from being told to "Ignore all previous instructions".
    # This is a soft sanitization.
    injection_patterns = [
        r"(?i)ignore\s+all\s+previous\s+instructions",
        r"(?i)system\s+prompt:",
        r"(?i)you\s+are\s+now\s+a",
        r"<script.*?>",
        r"javascript:",
    ]
    
    for pattern in injection_patterns:
        text = re.sub(pattern, "[CLEANED]", text)

    return text.strip()
