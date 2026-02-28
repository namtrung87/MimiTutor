import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key():
    return os.getenv("DASHBOARD_API_KEY", "dev-key-12345") # Fallback for dev

async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verifies the API key from the request header.
    """
    valid_key = get_api_key()
    if api_key == valid_key:
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )
