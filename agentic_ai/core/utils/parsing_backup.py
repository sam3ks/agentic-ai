# parsing.py
import re
import json
import numpy as np
import os
from sentence_transformers import SentenceTransformer
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
            "illegal interests", "miscellaneous"
        ]

def extract_purpose_with_regex_fallback(user_input: str, predefined_purposes: list) -> str:
    """
    Fallback method to extract purpose using regex patterns when sentence transformers fail.
    """
    # Enhanced regex patterns for common loan purposes
    purpose_patterns = {
        "education": r'\b(education|study|student|school|college|university|course|degree|tuition)\b',
        "home purchase": r'\b(home|house|property|flat|apartment|residential|real estate)\b.*\b(buy|purchase|buying)\b|\b(home|house)\s+loan\b',
        "vehicle purchase": r'\b(car|vehicle|auto|bike|motorcycle|scooter|truck|van)\b.*\b(buy|purchase|buying)\b|\b(car|vehicle|auto|bike)\s+loan\b',
        "medical emergency": r'\b(medical|health|hospital|treatment|surgery|medicine|doctor|emergency)\b',
        "business expansion": r'\b(business|startup|company|enterprise|expand|expansion|commercial)\b',
        "marriage": r'\b(marriage|wedding|ceremony|celebration)\b',
        "travel": r'\b(travel|trip|vacation|holiday|tour|tourism)\b',
        "debt consolidation": r'\b(debt|consolidat|refinanc|balance transfer|existing loan)\b',
        "luxury purchases": r'\b(luxury|premium|expensive|high-end|jewellery|jewelry|gold)\b'
    }
    
    for purpose, pattern in purpose_patterns.items():
        if re.search(pattern, user_input, re.IGNORECASE):
            print(f"[DEBUG] Regex match found for purpose: {purpose}")
            return purpose
    
    # If no specific pattern matches, check for general loan types
    if re.search(r'\b(personal|general)\s+loan\b', user_input, re.IGNORECASE):
        return "miscellaneous"
    
    return "unknown"

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
    is_likely_loan_request = any(phrase in user_input.lower() for phrase in loan_related_phrases)
    
    # If it doesn't look like a loan request at all, don't try to extract a purpose
    if not is_likely_loan_request:
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
        # Look for words that might be cities
        words = re.findall(r'\b[A-Z][a-z]{3,}\b', user_input)
        if words:
            for word in words:
                # Cities that aren't in our list will be handled by fuzzy matching later
                print(f"[DEBUG] Found potential city mention: {word}")
                loan_city = word  # This will be validated by the fuzzy matcher

    # Amount regex - keep using regex for this as it's more accurate for numeric extraction
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
        print(f"[DEBUG] Found amount: {loan_amount}")
    
    # Final debug output
    print(f"[DEBUG] Final parsed values - Purpose: '{loan_purpose}', Amount: {loan_amount}, City: '{loan_city}'")
    
    # Clean up purpose by removing filler words if we're still using a string from regex
    if loan_purpose != "unknown" and model is None:
        loan_purpose = re.sub(r'\b(for|a|an)\b', '', loan_purpose, re.IGNORECASE).strip()

    return {"purpose": loan_purpose, "amount": loan_amount, "city": loan_city}

def find_best_matching_purpose(user_input: str, model: SentenceTransformer, predefined_purposes: list, threshold: float = 0.65) -> str:
    """
    Find the best matching loan purpose from predefined purposes using semantic similarity.
    Includes checks to avoid matching general conversation to loan purposes.
    
    Args:
        user_input: The user's loan request text
        model: The SentenceTransformer model to use for encoding
        predefined_purposes: List of predefined loan purposes
        threshold: Minimum similarity score to consider a match (default: 0.65)
        
    Returns:
        The best matching purpose or "unknown" if no good match is found
    """
    try:
        print(f"[DEBUG] Matching loan purpose using semantic similarity for: '{user_input}'")
        
        # Encode the user input
        user_embedding = model.encode([user_input])
        
        # Define non-purpose phrases (general conversation)
        non_purpose_phrases = [
            "hello",
            "hi there",
            "how are you",
            "what's up",
            "good morning",
            "good afternoon", 
            "nice to meet you",
            "how's it going",
            "what can you do"
        ]
        
        # Check if input is closer to general conversation than loan purposes
        non_purpose_embeddings = model.encode(non_purpose_phrases)
        non_purpose_similarities = np.dot(user_embedding, non_purpose_embeddings.T)[0]
        max_non_purpose_similarity = np.max(non_purpose_similarities)
        
        # If input is very similar to general conversation, return "unknown"
        if max_non_purpose_similarity > 0.7:  # High threshold for general conversation
            print(f"[DEBUG] Input appears to be general conversation (similarity: {max_non_purpose_similarity:.4f})")
            return "unknown"
            
        # Encode the predefined purposes
        purpose_embeddings = model.encode(predefined_purposes)
        
        # Calculate cosine similarity between user input and all predefined purposes
        similarities = np.dot(user_embedding, purpose_embeddings.T)[0]
        
        # Find the top 3 matches for better debugging
        top_indices = np.argsort(similarities)[::-1][:3]
        for i, idx in enumerate(top_indices):
            print(f"[DEBUG] Match #{i+1}: '{predefined_purposes[idx]}' (score: {similarities[idx]:.4f})")
            
        # Find the purpose with the highest similarity score
        best_match_idx = top_indices[0]
        best_match_score = similarities[best_match_idx]
        best_match = predefined_purposes[best_match_idx]
        
        print(f"[DEBUG] Selected match: '{best_match}'")
        
        # Check for loan-related keywords to increase confidence
        loan_keywords = ["loan", "borrow", "money", "finance", "credit", "lend", "funding"]
        has_loan_keyword = any(keyword in user_input.lower() for keyword in loan_keywords)
        
        # Adjust threshold based on presence of loan keywords
        effective_threshold = threshold
        if not has_loan_keyword:
            # If no loan keyword is present, require a higher similarity score
            effective_threshold = 0.75
            
        # Return the matched purpose if it meets the threshold, otherwise "unknown"
        if best_match_score >= effective_threshold:
            print(f"[DEBUG] Purpose matched: '{best_match}'")
            return best_match
        else:
            print(f"[DEBUG] No purpose match above threshold {effective_threshold}")
            return "unknown"
    except Exception as e:
        print(f"[DEBUG] Error in purpose matching: {str(e)}")
        return "unknown"

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
        non_purpose_similarities = np.dot(user_embedding, non_purpose_embeddings.T)[0]
        max_non_purpose_similarity = np.max(non_purpose_similarities)
        
        if max_non_purpose_similarity > 0.7:
            print(f"[DEBUG] Input appears to be general conversation (similarity: {max_non_purpose_similarity:.4f})")
            return "not_detected"
        
        # Encode the enhanced purpose descriptions
        purpose_embeddings = model.encode(enhanced_purposes)
        
        # Calculate cosine similarity
        similarities = np.dot(user_embedding, purpose_embeddings.T)[0]
        
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

def create_enhanced_purpose_descriptions(predefined_purposes: list) -> list:
    """
    Create enhanced descriptions for better semantic matching.
    """
    enhanced_descriptions = []
    
    purpose_enhancements = {
        "education": "education loan for studies, school fees, college tuition, university expenses, course fees, academic learning",
        "home purchase": "home loan for buying house, purchasing property, real estate acquisition, residential property, flat purchase",
        "vehicle purchase": "vehicle loan for buying car, purchasing automobile, bike purchase, motorcycle, scooter, auto loan",
        "medical emergency": "medical loan for healthcare expenses, hospital bills, treatment costs, surgery, emergency medical needs",
        "business expansion": "business loan for company growth, startup funding, commercial expansion, enterprise development",
        "marriage": "marriage loan for wedding expenses, ceremony costs, celebration funding, matrimonial expenses",
        "travel": "travel loan for vacation, trip expenses, holiday funding, tourism, journey costs",
        "crypto trading": "cryptocurrency trading, digital asset investment, virtual currency, bitcoin, crypto speculation",
        "gambling": "gambling activities, betting, casino, lottery, speculation, gaming with money",
        "stock market trading": "stock trading, share market investment, equity trading, securities, stock speculation",
        "debt consolidation": "debt consolidation, refinancing existing loans, balance transfer, loan restructuring",
        "luxury purchases": "luxury items, expensive goods, premium products, high-end purchases, jewellery, gold",
        "illegal interests": "illegal activities, unlawful purposes, criminal enterprises, prohibited activities",
        "miscellaneous": "general purpose, personal needs, other requirements, miscellaneous expenses, unspecified use",
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
    explicit_loan_keywords = ["loan", "borrow", "finance", "credit", "funding"]
    has_explicit_keyword = any(keyword in user_input.lower() for keyword in explicit_loan_keywords)
    
    # Check for purpose-specific keywords
    purpose_keywords = [
        "buy", "purchase", "need", "want", "require", "looking for", "apply for",
        "education", "home", "car", "medical", "business", "travel", "marriage"
    ]
    has_purpose_keyword = any(keyword in user_input.lower() for keyword in purpose_keywords)
    
    # Adjust threshold based on context
    if has_explicit_keyword and has_purpose_keyword:
        # Strong loan context - lower threshold for easier matching
        return base_threshold - 0.1
    elif has_explicit_keyword or has_purpose_keyword:
        # Some loan context - use base threshold
        return base_threshold
    else:
        # Weak loan context - higher threshold for stricter matching
        return base_threshold + 0.15

def find_best_matching_purpose(user_input: str, model: SentenceTransformer, predefined_purposes: list, threshold: float = 0.65) -> str:
    """
    Find the best matching loan purpose from predefined purposes using semantic similarity.
    Includes checks to avoid matching general conversation to loan purposes.
    
    Args:
        user_input: The user's loan request text
        model: The SentenceTransformer model to use for encoding
        predefined_purposes: List of predefined loan purposes
        threshold: Minimum similarity score to consider a match (default: 0.65)
        
    Returns:
        The best matching purpose or "unknown" if no good match is found
    """
    try:
        print(f"[DEBUG] Matching loan purpose using semantic similarity for: '{user_input}'")
        
        # Encode the user input
        user_embedding = model.encode([user_input])
        
        # Define non-purpose phrases (general conversation)
        non_purpose_phrases = [
            "hello",
            "hi there",
            "how are you",
            "what's up",
            "good morning",
            "good afternoon", 
            "nice to meet you",
            "how's it going",
            "what can you do"
        ]
        
        # Check if input is closer to general conversation than loan purposes
        non_purpose_embeddings = model.encode(non_purpose_phrases)
        non_purpose_similarities = np.dot(user_embedding, non_purpose_embeddings.T)[0]
        max_non_purpose_similarity = np.max(non_purpose_similarities)
        
        # If input is very similar to general conversation, return "unknown"
        if max_non_purpose_similarity > 0.7:  # High threshold for general conversation
            print(f"[DEBUG] Input appears to be general conversation (similarity: {max_non_purpose_similarity:.4f})")
            return "unknown"
            
        # Encode the predefined purposes
        purpose_embeddings = model.encode(predefined_purposes)
        
        # Calculate cosine similarity between user input and all predefined purposes
        similarities = np.dot(user_embedding, purpose_embeddings.T)[0]
        
        # Find the top 3 matches for better debugging
        top_indices = np.argsort(similarities)[::-1][:3]
        for i, idx in enumerate(top_indices):
            print(f"[DEBUG] Match #{i+1}: '{predefined_purposes[idx]}' (score: {similarities[idx]:.4f})")
            
        # Find the purpose with the highest similarity score
        best_match_idx = top_indices[0]
        best_match_score = similarities[best_match_idx]
        best_match = predefined_purposes[best_match_idx]
        
        print(f"[DEBUG] Selected match: '{best_match}'")
        
        # Check for loan-related keywords to increase confidence
        loan_keywords = ["loan", "borrow", "money", "finance", "credit", "lend", "funding"]
        has_loan_keyword = any(keyword in user_input.lower() for keyword in loan_keywords)
        
        # Adjust threshold based on presence of loan keywords
        effective_threshold = threshold
        if not has_loan_keyword:
            # If no loan keyword is present, require a higher similarity score
            effective_threshold = 0.75
            
        # Return the matched purpose if it meets the threshold, otherwise "unknown"
        if best_match_score >= effective_threshold:
            print(f"[DEBUG] Purpose matched: '{best_match}'")
            return best_match
        else:
            print(f"[DEBUG] No purpose match above threshold {effective_threshold}")
            return "unknown"
    except Exception as e:
        print(f"[DEBUG] Error in purpose matching: {str(e)}")
        return "unknown"

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
        non_purpose_similarities = np.dot(user_embedding, non_purpose_embeddings.T)[0]
        max_non_purpose_similarity = np.max(non_purpose_similarities)
        
        if max_non_purpose_similarity > 0.7:
            print(f"[DEBUG] Input appears to be general conversation (similarity: {max_non_purpose_similarity:.4f})")
            return "not_detected"
        
        # Encode the enhanced purpose descriptions
        purpose_embeddings = model.encode(enhanced_purposes)
        
        # Calculate cosine similarity
        similarities = np.dot(user_embedding, purpose_embeddings.T)[0]
        
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

def create_enhanced_purpose_descriptions(predefined_purposes: list) -> list:
    """
    Create enhanced descriptions for better semantic matching.
    """
    enhanced_descriptions = []
    
    purpose_enhancements = {
        "education": "education loan for studies, school fees, college tuition, university expenses, course fees, academic learning",
        "home purchase": "home loan for buying house, purchasing property, real estate acquisition, residential property, flat purchase",
        "vehicle purchase": "vehicle loan for buying car, purchasing automobile, bike purchase, motorcycle, scooter, auto loan",
        "medical emergency": "medical loan for healthcare expenses, hospital bills, treatment costs, surgery, emergency medical needs",
        "business expansion": "business loan for company growth, startup funding, commercial expansion, enterprise development",
        "marriage": "marriage loan for wedding expenses, ceremony costs, celebration funding, matrimonial expenses",
        "travel": "travel loan for vacation, trip expenses, holiday funding, tourism, journey costs",
        "crypto trading": "cryptocurrency trading, digital asset investment, virtual currency, bitcoin, crypto speculation",
        "gambling": "gambling activities, betting, casino, lottery, speculation, gaming with money",
        "stock market trading": "stock trading, share market investment, equity trading, securities, stock speculation",
        "debt consolidation": "debt consolidation, refinancing existing loans, balance transfer, loan restructuring",
        "luxury purchases": "luxury items, expensive goods, premium products, high-end purchases, jewellery, gold",
        "illegal interests": "illegal activities, unlawful purposes, criminal enterprises, prohibited activities",
        "miscellaneous": "general purpose, personal needs, other requirements, miscellaneous expenses, unspecified use",
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
    explicit_loan_keywords = ["loan", "borrow", "finance", "credit", "funding"]
    has_explicit_keyword = any(keyword in user_input.lower() for keyword in explicit_loan_keywords)
    
    # Check for purpose-specific keywords
    purpose_keywords = [
        "buy", "purchase", "need", "want", "require", "looking for", "apply for",
        "education", "home", "car", "medical", "business", "travel", "marriage"
    ]
    has_purpose_keyword = any(keyword in user_input.lower() for keyword in purpose_keywords)
    
    # Adjust threshold based on context
    if has_explicit_keyword and has_purpose_keyword:
        # Strong loan context - lower threshold for easier matching
        return base_threshold - 0.1
    elif has_explicit_keyword or has_purpose_keyword:
        # Some loan context - use base threshold
        return base_threshold
    else:
        # Weak loan context - higher threshold for stricter matching
        return base_threshold + 0.15
