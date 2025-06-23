import json
from agentic_ai.core.agent.base_agent import BaseAgent
from agentic_ai.modules.loan_processing.services.loan_data_service import LoanDataService

class DataQueryAgent(BaseAgent):
    """Specialized agent for data querying."""

    def __init__(self, data_service: LoanDataService):
        super().__init__()
        self.data_service = data_service

    def query_user_data(self, query: str) -> str:
        """Queries user data with validation and processing."""
        try:
            # First, try direct validation without using LLM
            from agentic_ai.core.utils.validators import is_pan, is_aadhaar
            
            # Clean input to avoid any leading/trailing whitespace
            clean_query = query.strip()
            
            # Check if the cleaned input is directly a valid PAN or Aadhaar
            if is_pan(clean_query) or is_aadhaar(clean_query):
                identifier = clean_query
            else:
                # If direct validation fails, try LLM-based extraction
                validation_prompt = f"""Extract PAN or Aadhaar from: "{query}"

PAN format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F)
Aadhaar format: 12 digits (e.g., 123456789012)

Return only the identifier, nothing else. If neither is found, return "N/A"."""
                
                try:
                    identifier = self.llm._call(validation_prompt).strip()
                    if identifier == "N/A":
                        return json.dumps({"error": "No valid PAN or Aadhaar found in the query."})
                except Exception as e:
                    print(f"LLM parsing for identifier failed: {e}. Attempting direct parse.")
                    identifier = clean_query
                    if identifier.startswith('identifier:'):
                        identifier = identifier.split(':', 1)[1].strip()
            
            # Print a visual separator to highlight data query process
            print("\n" + "=" * 50)
            print("🔍 DATA QUERY ANALYSIS")
            print(f"🪪 Identifier: {identifier}")
            print(f"💭 Thought: Retrieving and analyzing user data with identifier {identifier}...")
            
            user_data = self.data_service.get_user_data(identifier)
            
            if "error" in user_data:
                print(f"💭 Thought: No matching user found for identifier {identifier}. This appears to be a new user.")
                print("=" * 50 + "\n")
                return json.dumps(user_data)
            
            if user_data.get("status") == "existing_user_data_retrieved":
                print(f"💭 Thought: Found existing user with identifier {identifier}. Analyzing their financial profile...")
                
                if 'city' in user_data:
                    del user_data['city']
                
                try:
                    monthly_salary = user_data.get('monthly_salary', 0)
                    credit_score = user_data.get('credit_score', 0)
                    existing_emi = user_data.get('existing_emi', 0)
                    
                    credit_rating = "Excellent" if credit_score >= 750 else "Good" if credit_score >= 700 else "Fair" if credit_score >= 650 else "Poor"
                    affordability = "High" if monthly_salary > 75000 else "Medium" if monthly_salary > 40000 else "Limited"
                    
                    print(f"💭 Thought: User has monthly salary of ₹{monthly_salary:,.0f}, credit score of {credit_score} ({credit_rating}), and existing EMI of ₹{existing_emi:,.0f}.")
                    print(f"💭 Thought: Based on income and existing obligations, affordability level is {affordability}.")
                    print("=" * 50 + "\n")
                    
                    analysis = {
                        "user_data": user_data,
                        "financial_assessment": {
                            "credit_rating": credit_rating,
                            "income_level": affordability,
                            "monthly_disposable_income": monthly_salary - existing_emi,
                            "existing_debt_burden": f"₹{existing_emi:,.0f} per month"
                        },
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
