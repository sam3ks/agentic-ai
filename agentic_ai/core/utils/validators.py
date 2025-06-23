import re

def is_pan(identifier: str) -> bool:
    """Checks if the identifier is a valid PAN."""
    return re.match(r'^[A-Z]{5}\d{4}[A-Z]$', identifier) is not None

def is_aadhaar(identifier: str) -> bool:
    """Checks if the identifier is a valid Aadhaar number.
    
    Accepts 12-digit numbers with or without spaces/dashes.
    """
    # First, remove any spaces, dashes or dots that might be present
    cleaned = re.sub(r'[\s\-\.]', '', identifier)
    # Then check if it's exactly 12 digits
    return re.match(r'^\d{12}$', cleaned) is not None
