"""
Validators Utility for Sclip
Provides input validation and sanitization for files, user input, and environment variables.
"""
import re
from typing import Any, Dict

# TODO: Add virus scanning, rate limiting, schema validation, etc.

def validate_filename(filename: str) -> bool:
    """Check if filename is safe and valid."""
    return bool(re.match(r'^[\w\-. ]+$', filename))

def validate_filetype(filename: str, allowed_types: Dict[str, list]) -> bool:
    """Check if file extension is allowed."""
    ext = filename.lower().rsplit('.', 1)[-1]
    return any(ext in exts for exts in allowed_types.values())

def validate_user_input(data: Any) -> bool:
    """Stub for user input validation (expand with schema checks)."""
    return data is not None

def sanitize_text(text: str) -> str:
    """Basic sanitization for user-provided text."""
    return re.sub(r'[<>"\'\\]', '', text)

def validate_env_vars(env: dict) -> bool:
    """Stub for environment variable validation."""
    # TODO: Check for required keys, value formats, etc.
    return True 