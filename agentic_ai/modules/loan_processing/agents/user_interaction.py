import os
from agentic_ai.core.agent.base_agent import BaseAgent
from agentic_ai.core.config.constants import AVAILABLE_CITIES

class UserInteractionAgent(BaseAgent):
    """Specialized agent for user interaction."""

    def __init__(self):
        self.reset_state()

    def reset_state(self):
        """Resets the state of the agent."""
        self._asked_purpose = False
        self._asked_amount = False
        self._asked_city = False
        self._asked_identification = False
        self._asked_salary_update = False
        self._asked_pdf_path = False
        self.initial_details = {}

    def set_initial_details(self, details: dict):
        """Sets the initial details extracted from the user's first message."""
        self.initial_details = details
        if details.get("purpose") and details["purpose"] != "unknown":
            self._asked_purpose = True
        if details.get("amount") and details["amount"] > 0:
            self._asked_amount = True
        if details.get("city") and details["city"] != "unknown":
            self._asked_city = True

    def handle_user_input(self, question: str) -> str:
        """Handles user interaction by prompting for actual input."""
        try:
            print(f"[DEBUG] UserInteractionAgent received question: {question}")

            # Enforce the required questions in the correct order
            if not self._asked_purpose and "pan" in question.lower():
                return "ERROR: You must ask for the loan PURPOSE first before collecting PAN/Aadhaar."
                
            if not self._asked_amount and self._asked_purpose and "pan" in question.lower():
                return "ERROR: You must ask for the loan AMOUNT after purpose but before collecting PAN/Aadhaar."

            is_required_city = "city" in question.lower() and "your city" in question.lower()
            is_required_loan_purpose = "purpose" in question.lower() or "what is the loan for" in question.lower()
            is_required_loan_amount = "amount" in question.lower() or "how much" in question.lower()
            is_salary_update_query = "update" in question.lower() and "salary" in question.lower()
            is_pdf_path_query = "pdf" in question.lower() or "salary slip" in question.lower() or "path" in question.lower()

            # If info is already known, return it instead of asking
            if is_required_loan_purpose and self.initial_details.get('purpose') and self.initial_details['purpose'] != 'unknown':
                return f"Based on the initial request, the loan purpose is '{self.initial_details['purpose']}'."
            if is_required_loan_amount and self.initial_details.get('amount') and self.initial_details['amount'] > 0:
                return f"Based on the initial request, the loan amount is '{self.initial_details['amount']}'."
            if is_required_city and self.initial_details.get('city') and self.initial_details['city'] != 'unknown':
                return f"Based on the initial request, the city is '{self.initial_details['city']}'."

            # Track what's been asked
            if is_required_loan_purpose:
                self._asked_purpose = True
            if is_required_loan_amount:
                self._asked_amount = True
            if "pan" in question.lower() or "aadhaar" in question.lower():
                self._asked_identification = True
            if is_required_city:
                self._asked_city = True
            if is_salary_update_query:
                self._asked_salary_update = True
            if is_pdf_path_query:
                self._asked_pdf_path = True
                print("📋 PDF path requested - This will be processed by the PDFSalaryExtractor")
            
            if is_required_city:
                city_list_str = ", ".join(AVAILABLE_CITIES)
                display_question = f"🤔 {question} (Please choose from: {city_list_str})"
                
                while True:
                    print(display_question)
                    user_response = input("Your response: ").strip()
                    
                    if not user_response:
                        print("⚠️ City is required. Please provide a valid city.")
                        continue
                    
                    normalized_response = user_response.lower().replace(" ", "")
                    valid_city_found = False
                    for city in AVAILABLE_CITIES:
                        if normalized_response == city.lower().replace(" ", ""):
                            user_response = city
                            valid_city_found = True
                            break
                    
                    if valid_city_found:
                        break
                    else:
                        print(f"⚠️ Invalid city: '{user_response}'. Please enter one of the available cities: {city_list_str}")
            
            elif is_required_loan_purpose:
                # For loan purpose - insist on getting a valid response
                display_question = f"🤔 {question} (This information is required to process your loan)"
                
                while True:
                    print(display_question)
                    user_response = input("Your response: ").strip()
                    
                    if not user_response:
                        print("⚠️ Loan purpose is required. Please provide a valid response.")
                        continue
                    
                    break  # Valid response received
                    
            elif is_required_loan_amount:
                # For loan amount - insist on getting a valid numeric response
                display_question = f"🤔 {question} (This information is required to process your loan)"
                
                while True:
                    print(display_question)
                    user_response = input("Your response: ").strip()
                    
                    if not user_response:
                        print("⚠️ Loan amount is required. Please provide a valid response.")
                        continue
                    
                    # Try to validate if it contains a number
                    import re
                    amount_match = re.search(r'\d+', user_response)
                    if not amount_match:
                        print("⚠️ Please include a numeric loan amount.")
                        continue
                    
                    break  # Valid response received
            
            elif is_pdf_path_query:
                # For PDF path question - detailed handling
                display_question = f"🤔 {question}"
                print(display_question)
                user_response = input("Your response: ").strip()
                
                # Validate the path has a PDF extension (or TXT for testing)
                if user_response and (user_response.lower().endswith('.pdf') or user_response.lower().endswith('.txt')):
                    print(f"📄 Path provided: {user_response}")
                    import os
                    if not os.path.exists(user_response):
                        print(f"⚠️ Warning: The file does not exist at the provided path. The PDF extraction may fail.")
                else:
                    print(f"⚠️ Warning: The path may not point to a PDF file. Make sure you've provided a proper PDF path.")
            
            else:
                # For other questions like PAN/Aadhaar
                display_question = f"🤔 {question}"
                print(display_question)
                user_response = input("Your response: ").strip()

            return user_response
        
        except Exception as e:
            print(f"[ERROR] UserInteractionAgent failed: {str(e)}")
            return f"An error occurred during user interaction: {str(e)}"

    def run(self, question: str) -> str:
        """Runs the agent with the given question."""
        return self.handle_user_input(question)
