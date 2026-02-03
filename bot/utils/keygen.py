"""
Key generation utilities.
"""
import secrets
import string
from bot.config import KEY_PREFIX, KEY_LENGTH


def generate_key() -> str:
    """
    Generate a unique redemption key.
    
    Format: PREFIX-XXXX-XXXX-XXXX
    Example: PREM-A1B2-C3D4-E5F6
    """
    chars = string.ascii_uppercase + string.digits
    
    # Generate random segments
    segments = []
    segment_length = 4
    num_segments = KEY_LENGTH // segment_length
    
    for _ in range(num_segments):
        segment = ''.join(secrets.choice(chars) for _ in range(segment_length))
        segments.append(segment)
    
    # Join with prefix
    return f"{KEY_PREFIX}-" + "-".join(segments)


def generate_simple_key(length: int = 16) -> str:
    """Generate a simple alphanumeric key without formatting."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def validate_key_format(key: str) -> bool:
    """
    Validate that a key matches the expected format.
    
    Args:
        key: The key string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    parts = key.split("-")
    
    if len(parts) < 2:
        return False
    
    # First part should be prefix
    if parts[0] != KEY_PREFIX:
        return False
    
    # Remaining parts should be 4 chars each, alphanumeric
    for part in parts[1:]:
        if len(part) != 4:
            return False
        if not part.isalnum():
            return False
    
    return True
