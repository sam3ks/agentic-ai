# formatting.py
"""
Utility functions for formatting data in the application.
"""

def format_indian_currency(amount: float) -> str:
    """
    Format a number as Indian currency (with lakhs and crores)
    
    Args:
        amount: The amount to format
    
    Returns:
        A formatted string with the Indian currency format (e.g. ₹1,23,456.00)
    """
    # Convert to string with 2 decimal places
    str_amount = f"{amount:.2f}"
    
    # Split the decimal part
    parts = str_amount.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else "00"
    
    # Format the integer part with commas for Indian numbering system
    # First, handle the last 3 digits
    result = ""
    if len(integer_part) > 3:
        result = "," + integer_part[-3:]
        # Then handle the rest in groups of 2
        integer_part = integer_part[:-3]
        while len(integer_part) > 0:
            if len(integer_part) >= 2:
                result = "," + integer_part[-2:] + result
                integer_part = integer_part[:-2]
            else:
                result = integer_part + result
                break
        # Remove leading comma if present
        if result.startswith(","):
            result = result[1:]
    else:
        result = integer_part
    
    # Add the decimal part and the rupee symbol
    return f"₹{result}.{decimal_part}"

def format_indian_currency_without_decimal(amount: float) -> str:
    """
    Format a number as Indian currency without decimal places (with lakhs and crores)
    
    Args:
        amount: The amount to format
    
    Returns:
        A formatted string with the Indian currency format without decimals (e.g. ₹1,23,456)
    """
    # Round to nearest integer
    rounded_amount = round(amount)
    
    # Convert to string
    str_amount = f"{rounded_amount}"
    
    # Format with commas for Indian numbering system
    result = ""
    if len(str_amount) > 3:
        result = "," + str_amount[-3:]
        # Then handle the rest in groups of 2
        str_amount = str_amount[:-3]
        while len(str_amount) > 0:
            if len(str_amount) >= 2:
                result = "," + str_amount[-2:] + result
                str_amount = str_amount[:-2]
            else:
                result = str_amount + result
                break
        # Remove leading comma if present
        if result.startswith(","):
            result = result[1:]
    else:
        result = str_amount
    
    # Add the rupee symbol
    return f"₹{result}"

def format_indian_commas(amount: float) -> str:
    """
    Format a number with Indian comma style (e.g. 1,00,000) without rupee symbol or decimals.
    """
    rounded_amount = round(amount)
    str_amount = f"{rounded_amount}"
    result = ""
    if len(str_amount) > 3:
        result = "," + str_amount[-3:]
        str_amount = str_amount[:-3]
        while len(str_amount) > 0:
            if len(str_amount) >= 2:
                result = "," + str_amount[-2:] + result
                str_amount = str_amount[:-2]
            else:
                result = str_amount + result
                break
        if result.startswith(","):
            result = result[1:]
    else:
        result = str_amount
    return result
