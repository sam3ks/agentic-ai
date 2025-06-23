# parsing.py
import re
import json
from agentic_ai.core.config.constants import AVAILABLE_CITIES

def extract_json_from_string(text: str) -> dict:
    """
    Extracts a JSON object from a string with improved robustness.
    """
    # Try to find JSON content enclosed in code blocks first (common in OpenAI responses)
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            # If parsing fails, continue with standard extraction
            pass
    
    # Find JSON-like content
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        # Clean up common issues that might cause parsing to fail
        json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
        json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            # Print the problematic JSON for debugging
            print(f"Problematic JSON: {json_str}")
            return {}
    
    # If no JSON is found, try to create one from key-value pairs in the text
    if ':' in text and ('"' in text or "'" in text):
        try:
            # Extract key-value pairs (simple heuristic)
            pattern = r'"([^"]+)":\s*(?:"([^"]+)"|(\d+))'
            matches = re.findall(pattern, text)
            if matches:
                result = {}
                for match in matches:
                    key = match[0]
                    value = match[2] if match[2] else match[1]
                    # Convert numeric strings to numbers
                    if value.isdigit():
                        value = int(value)
                    result[key] = value
                return result
        except Exception:
            pass
    
    return {}

def parse_initial_user_request(user_input: str) -> dict:
    """
    Parses the initial user request to extract loan purpose, amount, and city.
    """
    loan_purpose = "unknown"
    loan_amount = 0.0
    loan_city = "unknown"

    # Extract city
    for city in AVAILABLE_CITIES:
        if re.search(r'\b' + re.escape(city) + r'\b', user_input, re.IGNORECASE):
            loan_city = city
            break

    # More robust regex to capture purpose
    purpose_match = re.search(r'(?:loan for|for a|need a|i want a)\s+((?:an?|\s)*[\w\s]+?)(?:\s+loan)?', user_input, re.IGNORECASE)
    if purpose_match:
        loan_purpose = purpose_match.group(1).strip()
        # remove city from purpose if it was captured
        if loan_city != "unknown":
            loan_purpose = loan_purpose.replace(loan_city, "").strip()
    else:
        # Fallback for simple cases like "car loan"
        purpose_match = re.search(r'(\w+)\s+loan', user_input, re.IGNORECASE)
        if purpose_match:
            loan_purpose = purpose_match.group(1).strip()

    # Amount regex
    amount_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(lakhs?|million|crore)?', user_input, re.IGNORECASE)
    if amount_match:
        amount_str = amount_match.group(1).replace(',', '')
        loan_amount = float(amount_str)
        unit = (amount_match.group(2) or "").lower()
        if 'lakh' in unit:
            loan_amount *= 100000
        elif 'million' in unit:
            loan_amount *= 1000000
        elif 'crore' in unit:
            loan_amount *= 10000000
    
    # Clean up purpose if it still contains amount details
    if amount_match and loan_purpose != "unknown":
        loan_purpose = loan_purpose.replace(amount_match.group(0).strip(), "").strip()
        
    # Remove extra words from purpose
    loan_purpose = re.sub(r'\b(for|a|an)\b', '', loan_purpose, re.IGNORECASE).strip()

    return {"purpose": loan_purpose, "amount": loan_amount, "city": loan_city}
