#dataquery
import json
import requests
from agentic_ai.core.agent.base_agent import BaseAgent
from agentic_ai.modules.loan_processing.services.loan_data_service import LoanDataService
from agentic_ai.core.utils.formatting import format_indian_commas
 
class DataQueryAgent(BaseAgent):
    """Specialized agent for data querying."""
 
    def __init__(self, data_service: LoanDataService):
        super().__init__()
        self.data_service = data_service
 
    def _format_currency(self, amount):
        return format_indian_commas(amount)
   
    def fetch_credit_score_from_api(self, pan_number):
        """Fetch credit score from external API."""
        try:
            response = requests.post(
                "http://credit_score_api:5001/get_credit_score",
                json={"pan_number": pan_number},
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get("credit_score")
        except Exception as e:
            print(f"[API ERROR] Credit score API call failed: {e}")
        return None

    def query_user_data_silent(self, query: str) -> dict:
        """Silent version for security validation - returns raw data without verbose output."""
        try:
            from agentic_ai.core.utils.validators import is_pan, is_aadhaar
            clean_query = query.strip()
            aadhaar = None
            pan = None

            # Extract identifier
            if is_pan(clean_query):
                pan = clean_query
            elif is_aadhaar(clean_query):
                aadhaar = clean_query
            else:
                return {"error": "No valid PAN or Aadhaar found in the query."}

            # For security validation, we only need the basic user data lookup
            if aadhaar:
                user_data = self.data_service.get_user_data(aadhaar)
                return user_data
            elif pan:
                # Look up Aadhaar using PAN from CSV data
                aadhaar = self.data_service.get_aadhaar_by_pan(pan)
                if aadhaar:
                    user_data = self.data_service.get_user_data(aadhaar)
                    return user_data
                else:
                    return {"error": f"No user found for PAN {pan}"}
            else:
                return {"error": "No valid identifier provided"}
                
        except Exception as e:
            return {"error": f"Security validation failed: {str(e)}"}

    def fetch_aadhaar_details_from_api(self, aadhaar_number):
        """Fetch personal details from Aadhaar API."""
        try:
            response = requests.post(
                "http://aadhaar_api:5002/get_aadhaar_details",
                json={"aadhaar_number": aadhaar_number},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[API ERROR] Aadhaar details API call failed: {e}")
        return None
 
    def query_user_data(self, query: str) -> str:
        """Queries user data with Aadhaar for details and PAN for credit score only."""
        try:
            from agentic_ai.core.utils.validators import is_pan, is_aadhaar
            clean_query = query.strip()
            identifier = None
            aadhaar = None
            pan = None
 
 
 
            # Extract identifier
            if is_pan(clean_query):
                pan = clean_query
            elif is_aadhaar(clean_query):
                aadhaar = clean_query
            else:
                validation_prompt = f'''Extract PAN or Aadhaar from: "{query}"\n\nPAN format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F)\nAadhaar format: 12 digits (e.g., 123456789012)\n\nReturn only the identifier, nothing else. If neither is found, return "N/A".'''
                try:
                    identifier = self.llm._call(validation_prompt).strip()
                    print(f"[DEBUG] Extracted identifier from LLM: {identifier}")
                    if identifier == "N/A":
                        return json.dumps({"error": "No valid PAN or Aadhaar found in the query."})
                except Exception as e:
                    print(f"LLM parsing for identifier failed: {e}. Attempting direct parse.")
                    identifier = clean_query
                    if identifier.startswith('identifier:'):
                        identifier = identifier.split(':', 1)[1].strip()
                if is_pan(identifier):
                    pan = identifier
                elif is_aadhaar(identifier):
                    aadhaar = identifier
 
            # If only PAN is provided, look up Aadhaar using PAN
            if pan and not aadhaar:
                # Find Aadhaar linked to this PAN
                user_row = self.data_service.df[self.data_service.df['pan_number'] == pan]
                if not user_row.empty:
                    aadhaar = user_row.iloc[0]['aadhaar_number']
                else:
                    print(f"💭 Thought: PAN {pan} not found in records. This appears to be a new user.")
                    print("=" * 50 + "\n")
                    return json.dumps({
                        "status": "new_user_found_proceed_to_salary_sheet",
                        "message": "New user detected. Please provide salary information.",
                        "pan_provided": pan,
                        "instructions": "NEW USER: Ask for salary PDF upload directly. Do not ask about updating salary since they have no existing data."
                    })
 
            # If only Aadhaar is provided, use it
            if aadhaar:
                user_data = self.data_service.get_user_data(aadhaar)
            else:
                return json.dumps({"error": "No valid Aadhaar found for user data lookup."})
 
            # --- API call for credit score ---
            api_credit_score = None
            if pan:
                api_credit_score = self.fetch_credit_score_from_api(pan)
                print(f"[API] Credit score for PAN {pan}: {api_credit_score}")
                if api_credit_score is not None:
                    user_data['api_credit_score'] = api_credit_score
            else:
                # Suppress the "No PAN provided" message during security validation
                # We can detect this by checking if we're only querying with Aadhaar and no explicit PAN was expected
                api_credit_score = 0
                user_data['api_credit_score'] = api_credit_score
 
            # --- API call for Aadhaar personal details ---
            api_personal_details = None
            if aadhaar:
                api_personal_details = self.fetch_aadhaar_details_from_api(aadhaar)
                if api_personal_details:
                    print(f"[API] Personal details for Aadhaar {aadhaar}: {api_personal_details['name']}, {api_personal_details['age']} years, {api_personal_details['gender']}, Address: {api_personal_details.get('address', 'N/A')}")
                    user_data['api_personal_details'] = api_personal_details
                else:
                    print(f"[INFO] No personal details found for Aadhaar {aadhaar}")
            # --- end API calls ---
 
            if "error" in user_data:
                print(f"💭 Thought: No matching user found for Aadhaar {aadhaar}. This appears to be a new user.")
                print("=" * 50 + "\n")
                return json.dumps(user_data)
 
            if user_data.get("status") == "existing_user_data_retrieved":
                print(f"💭 Thought: Found existing user with Aadhaar {aadhaar}. Analyzing their financial profile...")
                if 'city' in user_data:
                    del user_data['city']
                try:
                    monthly_salary = user_data.get('monthly_salary', 0)
                    credit_score = user_data.get('api_credit_score', 0)
                    existing_emi = user_data.get('existing_emi', 0)
                    personal_details = user_data.get('api_personal_details', {})
                   
                    credit_rating = "Excellent" if credit_score >= 750 else "Good" if credit_score >= 700 else "Fair" if credit_score >= 650 else "Poor"
                    affordability = "High" if monthly_salary > 75000 else "Medium" if monthly_salary > 40000 else "Limited"
                   
                    print(f"💭 Thought: User has monthly salary of {self._format_currency(monthly_salary)}, credit score of {credit_score} ({credit_rating}), and existing EMI of {self._format_currency(existing_emi)}.")
                    if personal_details:
                        print(f"💭 Thought: Personal details - Name: {personal_details.get('name', 'N/A')}, Age: {personal_details.get('age', 'N/A')}, Gender: {personal_details.get('gender', 'N/A')}, Address: {personal_details.get('address', 'N/A')}, DOB: {personal_details.get('dob', 'N/A')}.")
                    print(f"💭 Thought: Based on income and existing obligations, affordability level is {affordability}.")
                    print("=" * 50 + "\n")
                   
                    analysis = {
                        "user_data": user_data,
                        "financial_assessment": {
                            "credit_rating": credit_rating,
                            "income_level": affordability,
                            "monthly_disposable_income": monthly_salary - existing_emi,
                            "existing_debt_burden": f"{self._format_currency(existing_emi)} per month"
                        },
                        "personal_details": personal_details if personal_details else {},
                        "status": "existing_user_found",
                        "action_needed": "ask_about_salary_update",
                        "message": "Existing user found. Ask if they want to update their salary information.",
                        "instructions": "EXISTING USER: First ask if they want to update salary information. If they say NO, use this complete user_data object for RiskAssessment. If they say YES, use PDFSalaryExtractor first."
                    }
                    return json.dumps(analysis, indent=2)
                except Exception as e:
                    return json.dumps({"user_data": user_data, "status": "data_retrieved", "info": f"Partial analysis due to error: {e}"}, indent=2)
            else:
                return json.dumps(user_data, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Data query error: {str(e)}"})
 
    def run(self, query: str) -> str:
        """Runs the agent's specific task."""
        return self.query_user_data(query)
 