#parsing.py
# Enhanced parsing.py with improved sentence-transformers implementation
import re
import json
import numpy as np
import os
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from agentic_ai.core.config.constants import AVAILABLE_CITIES
 
def load_loan_purpose_categories():
    """
    Load loan purpose categories from the policy JSON file.
    Returns a list of all available loan purpose categories.
    """
    try:
        # Get the path to the policy file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Navigate to the loan processing data directory
        policy_path = os.path.join(current_dir, '..', '..', 'modules', 'loan_processing', 'data', 'loan_purpose_policy.json')
        policy_path = os.path.abspath(policy_path)
       
        with open(policy_path, 'r') as f:
            policy_data = json.load(f)
       
        # Extract all categories
        categories = list(policy_data.keys())
        print(f"[DEBUG] Loaded {len(categories)} loan purpose categories from policy file")
        return categories
    except Exception as e:
        print(f"[DEBUG] Error loading loan purpose categories: {str(e)}")
        # Fallback to hardcoded list
        return [
            "education", "home purchase", "vehicle purchase", "medical emergency",
            "business expansion", "marriage", "travel", "crypto trading", "gambling",
            "stock market trading", "debt consolidation", "luxury purchases",
            "illegal interests", "miscellaneous", "not_detected"
        ]
 
def create_enhanced_purpose_descriptions(predefined_purposes: list) -> list:
    """
    Create enhanced descriptions for better semantic matching.
    """
    enhanced_descriptions = []
   
    purpose_enhancements = {
        "education": "education loan for studies, school fees, college tuition, university expenses, course fees, academic learning, student loan",
        "home purchase": "home loan for buying house, purchasing property, real estate acquisition, residential property, flat purchase, housing loan",
        "vehicle purchase": "vehicle loan for buying car, purchasing automobile, bike purchase, motorcycle, scooter, auto loan, car financing",
        "medical emergency": "medical loan for healthcare expenses, hospital bills, treatment costs, surgery, emergency medical needs, health loan",
        "business expansion": "business loan for company growth, startup funding, commercial expansion, enterprise development, working capital",
        "marriage": "marriage loan for wedding expenses, ceremony costs, celebration funding, matrimonial expenses, wedding financing",
        "travel": "travel loan for vacation, trip expenses, holiday funding, tourism, journey costs, travel financing",
        "crypto trading": "cryptocurrency trading, digital asset investment, virtual currency, bitcoin, crypto speculation, blockchain investment",
        "gambling": "gambling activities, betting, casino, lottery, speculation, gaming with money, wagering",
        "stock market trading": "stock trading, share market investment, equity trading, securities, stock speculation, market investment",
        "debt consolidation": "debt consolidation, refinancing existing loans, balance transfer, loan restructuring, debt management",
        "luxury purchases": "luxury items, expensive goods, premium products, high-end purchases, jewellery, gold, luxury shopping",
        "illegal interests": "illegal activities, unlawful purposes, criminal enterprises, prohibited activities, illicit transactions",
        "miscellaneous": "general purpose, personal needs, other requirements, miscellaneous expenses, unspecified use, personal loan",
        "not_detected": "unclear purpose, ambiguous request, unrelated to loans, general conversation"
    }
   
    for purpose in predefined_purposes:
        enhanced_desc = purpose_enhancements.get(purpose, purpose)
        enhanced_descriptions.append(enhanced_desc)
   
    return enhanced_descriptions
 
def adjust_threshold_based_on_context(user_input: str, base_threshold: float) -> float:
    """
    Adjust the similarity threshold based on the context and quality of the user input.
    """
    # Check for explicit loan keywords
    explicit_loan_keywords = ["loan", "borrow", "finance", "credit", "funding", "lend"]
    has_explicit_keyword = any(keyword in user_input.lower() for keyword in explicit_loan_keywords)
   
    # Check for purpose-specific keywords
    purpose_keywords = [
        "buy", "purchase", "need", "want", "require", "looking for", "apply for",
        "education", "home", "car", "medical", "business", "travel", "marriage"
    ]
    has_purpose_keyword = any(keyword in user_input.lower() for keyword in purpose_keywords)
   
    # Check for amount mentions which indicate serious loan inquiry
    has_amount = re.search(r'\b\d+\s*(lakh|crore|thousand|million|rupees|rs)\b', user_input, re.IGNORECASE)
   
    # Adjust threshold based on context
    if has_explicit_keyword and has_purpose_keyword:
        # Strong loan context - lower threshold for easier matching
        return max(0.35, base_threshold - 0.1)
    elif has_explicit_keyword or has_purpose_keyword or has_amount:
        # Some loan context - use base threshold
        return base_threshold
    else:
        # Weak loan context - higher threshold for stricter matching
        return min(0.85, base_threshold + 0.2)
 
def extract_purpose_with_regex_fallback(user_input: str, predefined_purposes: list) -> str:
    """
    Fallback method to extract purpose using regex patterns when sentence transformers fail.
    """
    # Enhanced regex patterns for common loan purposes
    purpose_patterns = {
        "education": r'\b(education|study|student|school|college|university|course|degree|tuition|academic)\b',
        "home purchase": r'\b(home|house|property|flat|apartment|residential|real estate)\b.*\b(buy|purchase|buying)\b|\b(home|house|housing)\s+loan\b',
        "vehicle purchase": r'\b(car|vehicle|auto|bike|motorcycle|scooter|truck|van)\b.*\b(buy|purchase|buying)\b|\b(car|vehicle|auto|bike)\s+loan\b',
        "medical emergency": r'\b(medical|health|hospital|treatment|surgery|medicine|doctor|emergency|healthcare)\b',
        "business expansion": r'\b(business|startup|company|enterprise|expand|expansion|commercial|working capital)\b',
        "marriage": r'\b(marriage|wedding|ceremony|celebration|matrimonial)\b',
        "travel": r'\b(travel|trip|vacation|holiday|tour|tourism|journey)\b',
        "debt consolidation": r'\b(debt|consolidat|refinanc|balance transfer|existing loan|restructur)\b',
        "luxury purchases": r'\b(luxury|premium|expensive|high-end|jewellery|jewelry|gold|diamond)\b'
    }
   
    for purpose, pattern in purpose_patterns.items():
        if re.search(pattern, user_input, re.IGNORECASE):
            print(f"[DEBUG] Regex match found for purpose: {purpose}")
            return purpose
   
    # If no specific pattern matches, check for general loan types
    if re.search(r'\b(personal|general)\s+loan\b', user_input, re.IGNORECASE):
        return "miscellaneous"
   
    return "unknown"
 
def find_best_matching_purpose_enhanced(user_input: str, model: SentenceTransformer, predefined_purposes: list, threshold: float = 0.45) -> str:
    """
    Enhanced version of find_best_matching_purpose with better semantic matching and context awareness.
    """
    try:
        print(f"[DEBUG] Enhanced semantic matching for: '{user_input}'")
       
        # Create enhanced purpose descriptions for better matching
        enhanced_purposes = create_enhanced_purpose_descriptions(predefined_purposes)
       
        # Encode the user input
        user_embedding = model.encode([user_input])
       
        # General conversation filtering
        non_purpose_phrases = [
            "hello", "hi there", "how are you", "what's up", "good morning",
            "good afternoon", "nice to meet you", "how's it going", "what can you do",
            "thanks", "thank you", "bye", "goodbye", "see you later"
        ]
       
        # Check if input is closer to general conversation
        non_purpose_embeddings = model.encode(non_purpose_phrases)
        # Compute cosine similarity properly
        non_purpose_similarities = cosine_similarity(user_embedding, non_purpose_embeddings)[0]
        max_non_purpose_similarity = np.max(non_purpose_similarities)
       
        if max_non_purpose_similarity > 0.7:
            print(f"[DEBUG] Input appears to be general conversation (similarity: {max_non_purpose_similarity:.4f})")
            return "not_detected"
       
        # Encode the enhanced purpose descriptions
        purpose_embeddings = model.encode(enhanced_purposes)
       
        # Calculate cosine similarity properly
        similarities = cosine_similarity(user_embedding, purpose_embeddings)[0]
       
        # Find top matches for debugging
        top_indices = np.argsort(similarities)[::-1][:5]
        for i, idx in enumerate(top_indices):
            print(f"[DEBUG] Match #{i+1}: '{predefined_purposes[idx]}' (score: {similarities[idx]:.4f})")
       
        # Get the best match
        best_match_idx = top_indices[0]
        best_match_score = similarities[best_match_idx]
        best_match = predefined_purposes[best_match_idx]
       
        # Context-aware threshold adjustment
        effective_threshold = adjust_threshold_based_on_context(user_input, threshold)
       
        # Return the matched purpose if it meets the threshold
        if best_match_score >= effective_threshold:
            print(f"[DEBUG] Enhanced purpose matched: '{best_match}' (score: {best_match_score:.4f})")
            return best_match
        else:
            print(f"[DEBUG] No purpose match above threshold {effective_threshold} (best score: {best_match_score:.4f})")
            # Try regex fallback before giving up
            regex_result = extract_purpose_with_regex_fallback(user_input, predefined_purposes)
            if regex_result != "unknown":
                print(f"[DEBUG] Regex fallback found: {regex_result}")
                return regex_result
            return "miscellaneous"  # Use miscellaneous instead of unknown for unclear purposes
           
    except Exception as e:
        print(f"[DEBUG] Error in enhanced purpose matching: {str(e)}")
        return "unknown"
 
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
    Uses enhanced sentence transformers for semantic purpose matching and regex for amount and city.
    """
    loan_purpose = "unknown"
    loan_amount = 0.0
    loan_city = "unknown"
 
    print(f"[DEBUG] Parsing initial request: {user_input}")
   
    # Load predefined purposes from policy JSON file
    predefined_purposes = load_loan_purpose_categories()
   
    # Check if the input appears to be a loan request at all
    loan_related_phrases = [
        "loan", "borrow", "lend", "finance", "credit", "money for", "need funds",
        "funding for", "want to buy", "purchase", "investing in", "financing",
        "need money", "require funds", "looking for", "apply for", "seeking"
    ]
    generic_purpose_phrases = [
        "need loan", "want loan", "loan required", "apply loan", "loan needed", "loan wanted", "loan", "i need loan", "i want loan"
    ]
    user_input_clean = user_input.strip().lower()
    is_likely_loan_request = any(phrase in user_input_clean for phrase in loan_related_phrases)
 
    # If input is too generic, force not_detected
    if any(phrase == user_input_clean or user_input_clean.startswith(phrase + " ") for phrase in generic_purpose_phrases):
        print(f"[DEBUG] Input '{user_input}' is too generic. Routing to 'not_detected'.")
        loan_purpose = "not_detected"
    elif not is_likely_loan_request:
        print("[DEBUG] Input doesn't appear to be a loan request")
        loan_purpose = "not_detected"
    else:
        # Try to identify the purpose using enhanced semantic matching with sentence transformers
        model = get_sentence_transformer_model()
        if model:
            # Find the best matching purpose semantically with enhanced matching
            loan_purpose = find_best_matching_purpose_enhanced(user_input, model, predefined_purposes, threshold=0.45)
        else:
            # Fallback to regex if model couldn't be loaded
            print("[DEBUG] Falling back to regex for purpose extraction")
            loan_purpose = extract_purpose_with_regex_fallback(user_input, predefined_purposes)
 
    # Extract city - will do a first pass with exact matches
    city_found = False
    for city in AVAILABLE_CITIES:
        if re.search(r'\b' + re.escape(city) + r'\b', user_input, re.IGNORECASE):
            loan_city = city
            print(f"[DEBUG] Found exact match for city: {loan_city}")
            city_found = True
            break
   
    # If no exact match, try to extract any city-like word for further processing
    if not city_found:
        # Look for words that might be cities - exclude common words that are not cities
        common_non_city_words = {
            'need', 'want', 'looking', 'hello', 'what', 'can', 'business', 'medical', 'planning',
            'loan', 'money', 'funds', 'finance', 'credit', 'purchase', 'buy', 'home', 'car',
            'education', 'travel', 'marriage', 'wedding', 'emergency', 'treatment', 'investment'
        }
       
        # Find capitalized words that could be cities
        words = re.findall(r'\b[A-Z][a-z]{3,}\b', user_input)
        if words:
            for word in words:
                if word.lower() not in common_non_city_words:
                    # Cities that aren't in our list will be handled by fuzzy matching later
                    print(f"[DEBUG] Found potential city mention: {word}")
                    loan_city = word  # This will be validated by the fuzzy matcher
                    break
       
        # Additional check for lowercase city names with common prefixes
        city_patterns = [r'\bin\s+([a-z]{4,})\b', r'\bfrom\s+([a-z]{4,})\b', r'\bat\s+([a-z]{4,})\b']
        for pattern in city_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match and not city_found:
                potential_city = match.group(1).title()
                if potential_city.lower() not in common_non_city_words:
                    print(f"[DEBUG] Found potential city from context: {potential_city}")
                    loan_city = potential_city
                    break
 
    # Amount regex - keep using regex for this as it's more accurate for numeric extraction
    amount_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(lakhs?|million|crore|thousand|rs|rupees)?', user_input, re.IGNORECASE)
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
        elif 'thousand' in unit:
            loan_amount *= 1000
        print(f"[DEBUG] Found amount: {loan_amount}")
   
    # Final debug output
    print(f"[DEBUG] Final parsed values - Purpose: '{loan_purpose}', Amount: {loan_amount}, City: '{loan_city}'")
   
    return {"purpose": loan_purpose, "amount": loan_amount, "city": loan_city}
 
def find_best_matching_purpose(user_input: str, model: SentenceTransformer, predefined_purposes: list, threshold: float = 0.65) -> str:
    """
    Legacy function for backward compatibility.
    Redirects to the enhanced version with adjusted threshold.
    """
    return find_best_matching_purpose_enhanced(user_input, model, predefined_purposes, threshold)
 
# Initialize the sentence transformer model (load only once for efficiency)
_sentence_transformer_model = None
 
def get_sentence_transformer_model():
    """
    Get or initialize the sentence transformer model.
    Uses lazy loading for efficiency.
    """
    global _sentence_transformer_model
    if _sentence_transformer_model is None:
        try:
            # Use a smaller but efficient model for faster inference
            _sentence_transformer_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
            print("[DEBUG] SentenceTransformer model loaded successfully")
        except Exception as e:
            print(f"[DEBUG] Error loading SentenceTransformer model: {str(e)}")
            return None
    return _sentence_transformer_model