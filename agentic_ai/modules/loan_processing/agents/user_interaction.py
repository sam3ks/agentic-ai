#user_interaction.py
import os
import re
from agentic_ai.core.agent.base_agent import BaseAgent
from agentic_ai.core.config.constants import AVAILABLE_CITIES
from agentic_ai.core.utils.fuzzy_matcher import CityMatcher
from agentic_ai.core.utils.formatting import format_indian_currency_without_decimal, format_indian_commas
 
class UserInteractionAgent(BaseAgent):
    """Specialized agent for user interaction."""
 
    def __init__(self, input_provider=None):
        super().__init__()
        self.input_provider = input_provider or input  # Default to built-in input()
        self.is_ui_mode = input_provider is not None and input_provider != input  # Detect UI mode
        self.reset_state()
        # Initialize the city matcher for fuzzy city name matching
        self.city_matcher = CityMatcher(AVAILABLE_CITIES)
        # Define restricted loan purposes that should be rejected

        self._restricted_purposes = [
            # Gambling related
            "gambling", "casino", "betting", "lottery", "poker", "sports betting", "wagering", "bingo", "slot machine", "bookmaker",

            # Illegal substances
            "drugs", "narcotics", "illegal substances", "controlled substances", "cocaine", "heroin", "meth", "lsd", "ecstasy",

            # Weapons
            "weapons", "firearms", "ammunition", "guns", "explosives", "bomb", "grenade", "knives", "assault rifle", "chemical weapon",

            # Financial risks - speculative or unregulated activities
            "cryptocurrency", "crypto", "nft", "token", "ico", "defi", "forex trading", "binary options", "unregulated investment",

            # Illegal activities
            "money laundering", "terrorist", "terrorism", "fraud", "scam", "pyramid scheme", "ponzi", "identity theft",
            "phishing", "smuggling", "black market", "counterfeit", "forgery", "bootlegging", "hacking", "cyber attack",
            "ransomware", "ddos", "malware", "spyware", "botnet", "data breach",

            # Other restricted
            "bribery", "illegal immigration", "extortion", "ransom", "human trafficking", "child exploitation",
            "hate speech", "incitement to violence",

            # High-risk industries or content
            "escort service", "adult entertainment", "cam site", "sex trafficking", "dark web", "deep web",
            "unlicensed pharmaceuticals", "unregulated medicine", "anabolic steroids", "counterfeit goods"
        ]

       
        # Define explicitly allowed personal purposes for reference
        self._personal_purpose_examples = [
            "personal expenses", "personal needs", "personal loan", "personal use",
            "life events", "daily needs", "family needs", "personal emergency"
        ]
 
        # Define termination keywords for exiting the interaction
        self._termination_keywords = {"stop", "quit", "terminate", "exit", "close", "end","cancel", "abort", "halt", "finish", "done", "enough", "bye",
    "goodbye", "disconnect", "logout","log out", "logoff", "conclude", "cease", "suspend", "break", "leave", "no more", "not interested", "not now", "not today", "stop this process"}
 
    def reset_state(self):
        """Resets the state of the agent and identity/consent flow."""
        self._asked_purpose = False
        self._asked_amount = False
        self._asked_city = False
        self._aadhaar_collected = False
        self._aadhaar_consent = False
        self._pan_collected = False
        self._pan_consent = False
        self._asked_salary_update = False
        self._asked_pdf_path = False
        self.initial_details = {}

    def get_user_input(self, prompt: str) -> str:
        """
        Get user input using the configured input provider.
        In UI mode, this returns the input directly without looping.
        """
        return self.input_provider(prompt)

    def _validate_input_with_retry(self, prompt: str, validation_func, error_message: str, max_retries: int = 3):
        """
        Helper method for input validation that respects UI mode.
        In CLI mode: loops until valid input or termination request
        In UI mode: validates once and returns result with error message if invalid
        
        Args:
            prompt: The prompt to show to user
            validation_func: Function that takes user input and returns (is_valid, processed_value)
            error_message: Message to show on validation failure
            max_retries: Maximum retries in UI mode (to prevent infinite loops)
        
        Returns:
            tuple: (success, value, message) where success is bool, value is the processed input, message is any error/info
        """
        retry_count = 0
        while True:
            if self.is_ui_mode and retry_count >= max_retries:
                print(f"[DEBUG] Max retries reached: {retry_count}")
                return False, None, f"Maximum retries exceeded. {error_message}"
            user_response = self.get_user_input(prompt).strip()
            print(f"[DEBUG] User input: '{user_response}' | Retry count: {retry_count}")
            if self._is_termination_request(user_response):
                print(f"You have chosen to exit. Exiting the process.")
                return False, "USER_EXIT", "User requested termination"
            is_pan_aadhaar = (
                ("pan" in prompt.lower() or "aadhaar" in prompt.lower())
                and ("consent" not in prompt.lower() and "accessing and processing" not in prompt.lower())
            )
            from agentic_ai.core.utils.validators import is_pan, is_aadhaar
            if is_pan_aadhaar:
                # Only skip incrementing retry count for empty input or initial user request
                if not user_response or user_response.startswith("User:"):
                    print(f"[DEBUG] Ignoring empty or initial request input for first prompt. Not incrementing retry count.")
                    prompt = f"Please provide your PAN or Aadhaar number."
                    continue
            is_valid, processed_value = validation_func(user_response)
            print(f"[DEBUG] Validation result: {is_valid}, Value: {processed_value}")
            if is_valid:
                return True, processed_value, "Success"
            else:
                print(f"{error_message}")
                if self.is_ui_mode:
                    print(f"[DEBUG] UI mode: returning error after invalid input.")
                    return False, None, error_message
                retry_count += 1
                print(f"[DEBUG] Incremented retry count: {retry_count}")
 
    def _is_termination_request(self, user_input: str) -> bool:
        """
        Checks if the user input contains any termination keywords.
        Tokenizes the input and checks if any token matches the termination list.
        """
        if not user_input:
            return False
        # Tokenize by splitting on spaces and check for keywords, removing common punctuation.
        tokens = user_input.lower().split()
        return any(token.strip(".,!?;:") in self._termination_keywords for token in tokens)
 
    def evaluate_purpose_with_llm(self, purpose: str) -> tuple:
        """
        Use the LLM to dynamically evaluate if a loan purpose is legal and ethical.
        This provides a more dynamic check that can catch novel illegal activities.
       
        Args:
            purpose: The loan purpose to evaluate
           
        Returns:
            tuple: (is_legal, message) where is_legal is a boolean and
                   message explains why it was rejected if illegal
        """
        if not purpose or purpose.lower() in ["unknown", "need", "want", "anything"]:
            return False, "Please provide a specific loan purpose."
 
        # Check if we have an LLM instance properly initialized
        if not hasattr(self, 'llm') or self.llm is None:
            print("[DEBUG] LLM not initialized, falling back to static validation")
            return self.validate_static_restrictions(purpose)
           
        # Craft a prompt for the LLM to evaluate the purpose
        prompt = f"""
You are a bank compliance officer responsible for evaluating loan applications.
Your task is to determine if the following loan purpose is legal, ethical, and compliant with banking regulations:
 
LOAN PURPOSE: "{purpose}"
 
EVALUATION CRITERIA:
1. Illegal activities: drugs, weapons, terrorism, fraud, hacking, theft, etc.
2. Prohibited loan uses: gambling, adult content, cryptocurrency
3. Money laundering risk: suspicious activities that could hide illegal sources of money
4. Regulatory compliance: any activity that might violate banking or financial regulations
 
IMPORTANT NOTES:
- Personal loan purposes ARE PERMITTED (examples: "personal expenses", "personal needs", "life events", "family needs")
- General purposes related to legitimate personal or family life needs ARE PERMITTED
- Vague purposes like "I need money" are acceptable but should be marked with a note for follow-up
 
INSTRUCTIONS:
- If there is ANY suspicion of illegal or prohibited activity, mark as "NO"
- If the purpose is legitimate, legal, or for personal/family needs, mark as "YES"
- Respond with YES if the purpose is legal, even if it's somewhat vague but not suspicious
 
Respond in the following format only:
IS_PERMITTED: [YES/NO]
REASON: [Brief explanation of your decision]
"""
        try:
            print(f"[DEBUG] Evaluating purpose with LLM: '{purpose}'")
            # Call the LLM to evaluate
            response = self.llm._call(prompt)
            print(f"[DEBUG] LLM response: {response}")
           
            # Parse the response
            is_permitted = False
            if "IS_PERMITTED: YES" in response and "IS_PERMITTED: NO" not in response:
                is_permitted = True
           
            # Extract reason from response
            reason = ""
            if "REASON:" in response:
                reason = response.split("REASON:")[1].strip()
                # Clean up any markdown backticks
                reason = reason.replace("```", "").strip()
           
            if is_permitted:
                print(f"[DEBUG] LLM approved purpose: '{purpose}'")
                return True, "Purpose accepted by compliance check"
            else:
                if not reason:
                    reason = "This purpose may violate our lending policy or regulations"
                print(f"[DEBUG] LLM rejected purpose: '{purpose}', reason: {reason}")
                return False, f"❌ LOAN REQUEST DENIED: {reason}"
               
        except Exception as e:
            print(f"[DEBUG] Error in LLM evaluation: {str(e)}")
            # Fallback to static validation if LLM fails
            return self.validate_static_restrictions(purpose)
   
    def validate_static_restrictions(self, purpose: str) -> tuple:
        """
        Fallback validation using static rules when LLM is unavailable.
       
        Args:
            purpose: The loan purpose to validate
           
        Returns:
            tuple: (is_valid, message)
        """
        # Convert to lowercase for case-insensitive matching
        purpose_lower = purpose.lower()
       
        # First check if this is an explicitly personal purpose
        for personal_purpose in self._personal_purpose_examples:
            if personal_purpose in purpose_lower:
                print(f"[DEBUG] Matched personal purpose: '{personal_purpose}' in '{purpose_lower}'")
                return True, "Personal purpose accepted"
       
        # Check against restricted purposes
        for restricted in self._restricted_purposes:
            if restricted in purpose_lower:
                return False, f"❌ LOAN REQUEST DENIED: We cannot approve loans for {restricted}-related activities as this violates our lending policy and may be illegal."
       
        # Check if it contains the word "personal" which generally indicates a personal loan
        if "personal" in purpose_lower:
            print(f"[DEBUG] Contains 'personal' keyword: '{purpose_lower}'")
            return True, "Personal purpose accepted"
       
        # Additional heuristic checks for potentially suspicious purposes
        suspicious_patterns = [
            (r'\billegal\b', "potentially illegal activities"),
            (r'\bblack\s*market\b', "black market activities"),
            (r'\bmoney\s*laundering\b', "money laundering"),
            (r'\bterrorist\b', "terrorism-related activities"),
            (r'\bfraud\b', "fraudulent activities"),
            (r'\bscam\b', "scam-related activities")
        ]
       
        for pattern, reason in suspicious_patterns:
            if re.search(pattern, purpose_lower):
                return False, f"❌ LOAN REQUEST DENIED: We cannot approve loans for {reason} as this violates our lending policy and may be illegal."
       
        # If we've reached here and it's not explicitly rejected, assume it's valid
        return True, "Purpose accepted"
 
    def validate_loan_purpose(self, purpose: str) -> tuple:
        """
        Validates that the loan purpose is legal and allowed.
        Uses both dynamic LLM evaluation and static rule-based validation.
       
        Args:
            purpose: The loan purpose to validate
           
        Returns:
            tuple: (is_valid, message)
        """
        # First try the dynamic LLM-based evaluation
        is_valid_llm, message_llm = self.evaluate_purpose_with_llm(purpose)
       
        # If LLM says it's not valid, reject immediately
        if not is_valid_llm:
            return False, message_llm
           
        # Double-check with static rules as a safeguard
        is_valid_static, message_static = self.validate_static_restrictions(purpose)
       
        # If either check fails, reject the purpose
        if not is_valid_static:
            return False, message_static
           
        return True, "Purpose accepted"
 
    def set_initial_details(self, details: dict):
        """Sets the initial details extracted from the user's first message."""
        self.initial_details = details
       
        print(f"[DEBUG] Initial details received: {details}")
       
        # If a loan purpose was extracted, mark it as already asked but DON'T validate
        # This allows the purpose to be passed directly to LoanPurposeAssessmentAgent
        if details.get("purpose") and details["purpose"] not in ["unknown", "need", "want", "not_detected"]:
            print(f"[DEBUG] Initial purpose detected: '{details['purpose']}' - will be evaluated by LoanPurposeAssessmentAgent")
            self._asked_purpose = True
        else:
            print(f"[DEBUG] No valid initial purpose found, got: '{details.get('purpose', 'None')}' - will need to ask user")
        if details.get("amount") and details["amount"] > 0:
            # Import formatting utility
            from agentic_ai.core.utils.formatting import format_indian_currency_without_decimal
            print(f"[DEBUG] Initial amount is valid: {format_indian_currency_without_decimal(details['amount'])}")
            self._asked_amount = True
       
        if details.get("city") and details["city"] != "unknown":
            # Try to match the provided city using fuzzy matching
            matched_city, score = self.city_matcher.get_closest_match(details["city"])
            if matched_city:
                if matched_city != details["city"]:
                    print(f"[DEBUG] Normalized city from '{details['city']}' to '{matched_city}' (score: {score}%)")
                    self.initial_details["city"] = matched_city
                print(f"[DEBUG] Initial city is valid: {matched_city}")
                self._asked_city = True
            else:
                print(f"[DEBUG] Initial city '{details['city']}' could not be matched to a supported city")
                self.initial_details["city"] = "unknown"
 
    def get_user_input(self, prompt):
        return self.input_provider(prompt)
 
    def handle_user_input(self, question: str) -> str:
        """Handles user interaction by prompting for actual input, enforcing Aadhaar/PAN/consent flow and color output for consent."""
        try:
            print(f"[DEBUG] UserInteractionAgent received question: {question}")
            from agentic_ai.core.utils.validators import is_pan, is_aadhaar
 
            # ANSI color codes - only use in CLI mode
            if not self.is_ui_mode:
                YELLOW = '\033[93m'
                GREEN = '\033[92m'
                RED = '\033[91m'
                RESET = '\033[0m'
            else:
                # No color codes in UI mode
                YELLOW = GREEN = RED = RESET = ''
 
 
            # Only run the identity/consent flow if not already completed and only at the correct stage
            # Aadhaar/PAN/consent strict flow should only be triggered after loan purpose is confirmed
            is_required_loan_purpose = "purpose" in question.lower() or "what is the loan for" in question.lower()
            is_required_loan_amount = "amount" in question.lower() or "how much" in question.lower()
            is_asking_for_aadhaar = ("aadhaar" in question.lower()) and not ("pan" in question.lower())
            is_asking_for_pan = ("pan" in question.lower()) and not ("aadhaar" in question.lower())
            is_asking_for_both = ("pan" in question.lower() and "aadhaar" in question.lower())
 
            # Only trigger Aadhaar/PAN/consent flow if the question is specifically for Aadhaar or PAN
            if (is_asking_for_aadhaar or is_asking_for_both) and not self._aadhaar_collected:
                def validate_aadhaar(user_input):
                    if is_aadhaar(user_input):
                        return True, user_input
                    elif is_pan(user_input):
                        return False, "PAN number cannot be accepted as the first input. Please start with your Aadhaar number."
                    else:
                        return False, "Invalid Aadhaar number. Please enter a valid 12-digit Aadhaar number."
                
                success, value, message = self._validate_input_with_retry(
                    f"{YELLOW}🪪 Please enter your Aadhaar number:{RESET}",
                    validate_aadhaar,
                    f"{RED}❌ Invalid input. Please check and try again.{RESET}"
                )
                
                if not success:
                    if value == "USER_EXIT":
                        print(f"{RED}You have chosen to exit. Exiting the process.{RESET}")
                        return "USER_EXIT"
                    elif self.is_ui_mode:
                        # In UI mode, return error message to let UI handle it
                        return f"ERROR: {message}"
                else:
                    self._aadhaar_collected = True
                    self._aadhaar_number = value
 
            if (is_asking_for_aadhaar or is_asking_for_both) and self._aadhaar_collected and not self._aadhaar_consent:
                def validate_consent(user_input):
                    consent = user_input.lower()
                    if consent in ["yes", "y"]:
                        return True, True
                    elif consent in ["no", "n"]:
                        return True, False
                    else:
                        return False, "Please answer 'yes' or 'no'."
                
                success, value, message = self._validate_input_with_retry(
                    f"{YELLOW}🔒 Do you consent to us accessing and processing your Aadhaar-linked information? (yes/no){RESET}",
                    validate_consent,
                    f"{YELLOW}Please answer 'yes' or 'no'.{RESET}"
                )
                
                if not success:
                    if value == "USER_EXIT":
                        print(f"{RED}You have chosen to exit. Exiting the process.{RESET}")
                        return "USER_EXIT"
                    elif self.is_ui_mode:
                        return f"ERROR: {message}"
                else:
                    if value:
                        print(f"{GREEN}✅ Consent received for Aadhaar processing.{RESET}")
                        self._aadhaar_consent = True
                    else:
                        print(f"{RED}Consent not given. The process will be terminated.{RESET}")
                        return "USER_EXIT"
 
 
            if (is_asking_for_pan or is_asking_for_both) and self._aadhaar_collected and self._aadhaar_consent and not self._pan_collected:
                def validate_pan(user_input):
                    if is_pan(user_input):
                        # SECURITY CHECK: Ensure PAN matches the one linked to the Aadhaar
                        try:
                            from agentic_ai.modules.loan_processing.services.loan_data_service import LoanDataService
                            data_service = LoanDataService()
                            user_row = data_service.df[data_service.df['aadhaar_number'] == self._aadhaar_number]
                            if not user_row.empty:
                                expected_pan = user_row.iloc[0]['pan_number']
                                if expected_pan.upper().strip() != user_input.upper().strip():
                                    return False, "SECURITY ALERT: The PAN you entered does not match the PAN linked to your Aadhaar. Please check and enter the correct PAN. The process will be terminated for your security."
                            return True, user_input
                        except Exception as e:
                            return False, f"Security check failed: {e}"
                    elif is_aadhaar(user_input):
                        return False, "Aadhaar number already provided. Please enter your PAN number now."
                    else:
                        return False, "Invalid PAN number. Please enter a valid PAN (e.g., ABCDE1234F)."
                
                success, value, message = self._validate_input_with_retry(
                    f"{YELLOW}📝 Please enter your PAN number:{RESET}",
                    validate_pan,
                    f"{RED}❌ Invalid input. Please check and try again.{RESET}"
                )
                
                if not success:
                    if value == "USER_EXIT":
                        print(f"{RED}You have chosen to exit. Exiting the process.{RESET}")
                        return "USER_EXIT"
                    elif "SECURITY ALERT" in message:
                        print(f"{RED}❌ {message}{RESET}")
                        return "USER_EXIT"
                    elif self.is_ui_mode:
                        return f"ERROR: {message}"
                else:
                    self._pan_collected = True
                    self._pan_number = value
 
            if (is_asking_for_pan or is_asking_for_both) and self._aadhaar_collected and self._aadhaar_consent and self._pan_collected and not self._pan_consent:
                def validate_pan_consent(user_input):
                    consent = user_input.lower()
                    if consent in ["yes", "y"]:
                        return True, True
                    elif consent in ["no", "n"]:
                        return True, False
                    else:
                        return False, "Please answer 'yes' or 'no'."
                
                success, value, message = self._validate_input_with_retry(
                    f"{YELLOW}🔒 Do you consent to us accessing and processing your PAN-linked data (financial details, credit score, etc.)? (yes/no){RESET}",
                    validate_pan_consent,
                    f"{YELLOW}Please answer 'yes' or 'no'.{RESET}"
                )
                
                if not success:
                    if value == "USER_EXIT":
                        print(f"{RED}You have chosen to exit. Exiting the process.{RESET}")
                        return "USER_EXIT"
                    elif self.is_ui_mode:
                        return f"ERROR: {message}"
                else:
                    if value:
                        print(f"{GREEN}✅ Consent received for PAN processing.{RESET}")
                        self._pan_consent = True
                    else:
                        print(f"{RED}Consent not given. The process will be terminated.{RESET}")
                        return "USER_EXIT"
 
            if (is_asking_for_aadhaar or is_asking_for_pan or is_asking_for_both) and not (self._aadhaar_collected and self._aadhaar_consent and self._pan_collected and self._pan_consent):
                print(f"{RED}Identity verification and consent sequence not completed. Cannot proceed.{RESET}")
                return "USER_EXIT"
 
            # After identity/consent, handle further questions as before
            # ...existing code for other questions (purpose, amount, city, etc.)...
            is_required_city = "city" in question.lower() and "your city" in question.lower()
            is_required_loan_purpose = "purpose" in question.lower() or "what is the loan for" in question.lower()
            is_required_loan_amount = "amount" in question.lower() or "how much" in question.lower()
            is_salary_update_query = "update" in question.lower() and "salary" in question.lower()
            is_pdf_path_query = "pdf" in question.lower() or "salary slip" in question.lower() or "path" in question.lower()
 
            # Prevent repeated PAN/Aadhaar prompts: if the question is for PAN/Aadhaar and already collected, just return the PAN (or Aadhaar) already provided
            if ("pan" in question.lower() or "aadhaar" in question.lower()) and self._aadhaar_collected and self._aadhaar_consent and self._pan_collected and self._pan_consent:
                # Prefer PAN if available, else Aadhaar
                if hasattr(self, '_pan_number') and self._pan_number:
                    return self._pan_number
                elif hasattr(self, '_aadhaar_number') and self._aadhaar_number:
                    return self._aadhaar_number
                else:
                    return ""
 
            if is_required_loan_purpose and self.initial_details.get("purpose") and self.initial_details["purpose"] not in ["unknown", "need", "want", "not_detected"]:
                self._asked_purpose = True
                return f"Based on the initial request, the loan purpose is '{self.initial_details['purpose']}'."
 
            if is_required_loan_amount and self.initial_details.get("amount") and self.initial_details["amount"] > 0:
                return f"Based on the initial request, the loan amount is '{format_indian_commas(self.initial_details['amount'])}'."
 
            if is_required_city and self.initial_details.get("city") and self.initial_details["city"] != "unknown":
                matched_city, score = self.city_matcher.get_closest_match(self.initial_details["city"])
                if matched_city:
                    if matched_city != self.initial_details["city"]:
                        old_city = self.initial_details["city"]
                        self.initial_details["city"] = matched_city
                        return f"Based on the initial request, we recognized '{old_city}' as '{matched_city}'."
                    return f"Based on the initial request, the city is '{self.initial_details['city']}'."
                else:
                    self.initial_details["city"] = "unknown"
 
            if is_required_loan_purpose:
                self._asked_purpose = True
            if is_required_loan_amount:
                self._asked_amount = True
            if is_required_city:
                self._asked_city = True
            if is_salary_update_query:
                self._asked_salary_update = True
            if is_pdf_path_query:
                self._asked_pdf_path = True
 
            # Ask city with fuzzy validation
            if is_required_city:
                city_list_str = ", ".join(AVAILABLE_CITIES)
                
                def validate_city(user_input):
                    if not user_input:
                        return False, "City is required."
                    matched_city, score = self.city_matcher.get_closest_match(user_input)
                    if matched_city:
                        if score == 100:
                            print(f"{GREEN}✓ Recognized city: {matched_city}{RESET}")
                        else:
                            print(f"{GREEN}✓ Recognized '{user_input}' as '{matched_city}' (match score: {score}%){RESET}")
                        return True, matched_city
                    elif score > 50:
                        return False, f"Did you mean one of our supported cities? Your entry '{user_input}' was not recognized. Available options: {city_list_str}"
                    else:
                        return False, f"Invalid city. Please select from: {city_list_str}"
                
                success, value, message = self._validate_input_with_retry(
                    f"{YELLOW}🤔 {question} (Available options: {city_list_str}){RESET}",
                    validate_city,
                    f"{RED}⚠️ Invalid city selection.{RESET}"
                )
                
                if not success:
                    if value == "USER_EXIT":
                        print(f"{RED}You have chosen to exit. Exiting the process.{RESET}")
                        return "USER_EXIT"
                    elif self.is_ui_mode:
                        return f"ERROR: {message}"
                else:
                    return value
 
            elif is_required_loan_purpose:
                def validate_purpose(user_input):
                    if not user_input or user_input.lower() in ["need", "want", "anything"]:
                        return False, "Please provide a clear loan purpose like 'home renovation', 'medical', etc."
                    if any(term in user_input.lower() for term in ["illegal", "drugs", "weapons", "terrorism"]):
                        return False, "Please provide a legal and acceptable loan purpose."
                    return True, user_input
                
                success, value, message = self._validate_input_with_retry(
                    f"{YELLOW}🤔 {question} (You can leave this process anytime if you wish){RESET}",
                    validate_purpose,
                    f"{RED}⚠️ Invalid loan purpose.{RESET}"
                )
                
                if not success:
                    if value == "USER_EXIT":
                        print(f"{RED}You have chosen to exit. Exiting the process.{RESET}")
                        return "USER_EXIT"
                    elif self.is_ui_mode:
                        return f"ERROR: {message}"
                else:
                    return value
 
            elif is_required_loan_amount:
                def validate_amount(user_input):
                    if not user_input:
                        return False, "Loan amount is required."
                    if not re.search(r'\d+', user_input):
                        return False, "Please enter a number."
                    return True, user_input
                
                success, value, message = self._validate_input_with_retry(
                    f"{YELLOW}🤔 {question} (Please enter a numeric value, or type 'stop' to exit){RESET}",
                    validate_amount,
                    f"{RED}⚠️ Invalid loan amount.{RESET}"
                )
                
                if not success:
                    if value == "USER_EXIT":
                        print(f"{RED}You have chosen to exit. Exiting the process.{RESET}")
                        return "USER_EXIT"
                    elif self.is_ui_mode:
                        return f"ERROR: {message}"
                else:
                    return value
 
            elif is_pdf_path_query:
                def validate_pdf_path(user_input):
                    if user_input and (user_input.lower().endswith(".pdf") or user_input.lower().endswith(".txt")):
                        # In UI mode, be more lenient with file paths - let the PDF extractor handle it
                        if self.is_ui_mode:
                            return True, user_input
                        # In CLI mode, check if file exists
                        if not os.path.exists(user_input):
                            print(f"{YELLOW}⚠️ Warning: File does not exist.{RESET}")
                        return True, user_input
                    else:
                        return False, "Please provide a valid .pdf or .txt file path."
                
                success, value, message = self._validate_input_with_retry(
                    f"{YELLOW}🤔 {question}{RESET}",
                    validate_pdf_path,
                    f"{RED}⚠️ Please provide a valid PDF or text file path.{RESET}"
                )
                
                if not success:
                    if value == "USER_EXIT":
                        print(f"{RED}You have chosen to exit. Exiting the process.{RESET}")
                        return "USER_EXIT"
                    elif self.is_ui_mode:
                        return f"ERROR: {message}"
                else:
                    return value
 
            # Fallback for any other question
            return self.get_user_input(f"{YELLOW}🤔 {question}{RESET}")
 
        except Exception as e:
            print(f"[ERROR] UserInteractionAgent failed: {str(e)}")
            return f"An error occurred: {str(e)}"
 
    def run(self, question: str) -> str:
        response = self.handle_user_input(question)
        if response == "USER_EXIT":
            print("User exited the process.")
            # Stop the agent chain or return a special result
            return "USER_EXIT"
        return response
 
    def _format_currency(self, amount):
        return format_indian_commas(amount)