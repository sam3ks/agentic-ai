import json
import re
import os
from typing import Dict, Any, Optional
from agentic_ai.core.agent.base_agent import BaseAgent
from agentic_ai.core.utils.parsing import extract_json_from_string
from agentic_ai.core.utils.formatting import format_indian_commas

class GeoPolicyAgent(BaseAgent):
    """Specialized agent for geographic policy validation."""
    
    def __init__(self):
        super().__init__()
        self.purpose_policy_data = self._load_purpose_policy_data()
    
    def _load_purpose_policy_data(self) -> Dict[str, Any]:
        """Load loan purpose policy data from JSON file."""
        try:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to the loan_processing module and then into the data directory
            data_dir = os.path.join(os.path.dirname(current_dir), "data")
            policy_path = os.path.join(data_dir, "loan_purpose_policy.json")
            
            if os.path.exists(policy_path):
                with open(policy_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}
    
    def _check_purpose_eligibility(self, purpose: str) -> Optional[Dict[str, Any]]:
        """Check if the purpose is eligible based on policy."""
        if not self.purpose_policy_data:
            return None
        
        # Direct match first
        if purpose in self.purpose_policy_data:
            return self.purpose_policy_data.get(purpose)
        
        # Case-insensitive search
        purpose_lower = purpose.lower()
        for key, value in self.purpose_policy_data.items():
            if key.lower() == purpose_lower:
                return value
        
        return None

    def validate_geo_policy(self, query: str) -> str:
        """Validates geographic policies using LLM reasoning."""
        try:
            # HARD CHECK: First, ensure the input follows the EXACT format before doing anything else
            if not query.startswith('city:'):
                return json.dumps({
                    "error": "CRITICAL ERROR: City information missing or not in correct format",
                    "status": "rejected",
                    "action_required": "You MUST explicitly ask for the user's city using UserInteraction tool and use format 'city:CITY_NAME,purpose:LOAN_PURPOSE,amount:LOAN_AMOUNT'",
                    "correct_format": "city:Mumbai,purpose:personal,amount:100000"
                })
                
            # Parse the city, purpose, and amount from the query using regex
            city_match = re.search(r'city:([^,]+)', query)
            purpose_match = re.search(r'purpose:([^,]+)', query)
            amount_match = re.search(r'amount:(\d+)', query)
            
            # If any required field is missing, reject immediately
            if not city_match or not purpose_match or not amount_match:
                return json.dumps({
                    "error": "CRITICAL ERROR: Required fields missing",
                    "status": "rejected",
                    "action_required": "You MUST provide all three required fields: city, purpose, and amount",
                    "correct_format": "city:Mumbai,purpose:personal,amount:100000"
                })
                
            # Extract the values
            city = city_match.group(1).strip()
            purpose = purpose_match.group(1).strip()
            try:
                amount = float(amount_match.group(1).strip())
            except ValueError:
                return json.dumps({
                    "error": "CRITICAL ERROR: Invalid loan amount",
                    "status": "rejected",
                    "action_required": "Amount must be a valid number"
                })
            
            # Check purpose eligibility from the policy data
            purpose_policy = self._check_purpose_eligibility(purpose)
            if purpose_policy and purpose_policy.get("eligibility") == "prohibited":
                return json.dumps({
                    "error": f"CRITICAL ERROR: Loan purpose '{purpose}' is prohibited",
                    "status": "rejected",
                    "reason": purpose_policy.get("reason", "This purpose is not eligible for loans according to our policy."),
                    "notes": purpose_policy.get("notes", ""),
                    "policy_ref": purpose_policy.get("policy_ref", ""),
                    "action_required": "Please inform the user that this loan purpose is not eligible."
                })
            
            # Proceed with the normal validation
            # Add policy category to the prompt if available
            category_info = ""
            if purpose_policy:
                category_info = f"\nLoan Category: {purpose_policy.get('category', 'N/A')}"
                
            parsing_prompt = f"""
You are a loan policy expert. Parse this geographic policy validation request:

Query: "{query}"

Extract and validate:
1. City name
2. Loan purpose/type
3. Loan amount

Indian cities we serve: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Surat, Jaipur

You MUST respond ONLY with a valid JSON object in the EXACT format shown below:

{{
    "city": "extracted_city",
    "purpose": "normalized_purpose",
    "amount": numeric_amount,
    "valid_request": true,
    "errors": []
}}

Ensure all fields are present, with "city" as a string, "purpose" as a string, "amount" as a numeric value, "valid_request" as a boolean, and "errors" as an array of strings (empty if valid_request is true).
DO NOT include any text or explanation outside of the JSON.
{category_info}
"""
            try:
                parsing_result = self.llm._call(parsing_prompt)
                parsed_data = extract_json_from_string(parsing_result)

                # Validate that parsed_data has all required fields
                if not parsed_data:
                    print(f"⚠️ Empty parsing result or extraction failed. Raw result: {parsing_result}")
                    # Check if the input follows the expected format - city:name,purpose:type,amount:value
                    format_check = re.search(r'city:([^,]+),purpose:([^,]+),amount:(\d+)', query)
                    
                    if format_check:
                        city = format_check.group(1).strip()
                        purpose = format_check.group(2).strip()
                        try:
                            amount = float(format_check.group(3).strip())
                        except ValueError:
                            amount = 0
                        
                        # Create result with extracted values
                        parsed_data = {
                            "city": city,
                            "purpose": purpose,
                            "amount": amount,
                            "valid_request": True,
                            "errors": []
                        }
                    else:
                        # Do not make assumptions - explicitly reject wrong format
                        return json.dumps({
                            "error": "Invalid format for GeoPolicyCheck",
                            "status": "rejected",
                            "action_required": "Format must be: city:{CITY},purpose:{PURPOSE},amount:{AMOUNT}",
                            "example": "city:Mumbai,purpose:personal,amount:100000"
                        })
            except Exception as e:
                print(f"⚠️ Policy parsing error: {str(e)}")
                return json.dumps({"error": f"Policy parsing service unavailable: {str(e)}"})
            
            # Validate request
            if not parsed_data.get("valid_request", False):
                error_msg = ', '.join(parsed_data.get('errors', ["Invalid request"]))
                return json.dumps({"info": f" Message: {error_msg}"})
            
            city = parsed_data.get("city", "Unknown")
            purpose = parsed_data.get("purpose", "Unknown")
            amount = parsed_data.get("amount", 0)
            
            # Strict validation for required fields - no more guessing or defaults
            if city == "Unknown" or city.lower() not in ['mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 'ahmedabad', 'surat', 'jaipur']:
                return json.dumps({
                    "error": "Missing or invalid city",
                    "status": "rejected",
                    "action_required": "Please ask the user for their city explicitly. Valid cities: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Surat, Jaipur"
                })
            
            if purpose == "Unknown":
                return json.dumps({
                    "error": "Missing loan purpose",
                    "status": "rejected",
                    "action_required": "Please ask the user for the loan purpose explicitly."
                })
            
            if amount <= 0:
                return json.dumps({
                    "error": "Missing or invalid loan amount",
                    "status": "rejected", 
                    "action_required": "Please ask the user for a valid loan amount explicitly."
                })

            # Import formatting utility
            from agentic_ai.core.utils.formatting import format_indian_currency_without_decimal
            
            policy_prompt = f"""
You are a senior loan policy officer. Make a geographic policy decision for this loan:

City: {city}
Loan Purpose: {purpose}{category_info}
Loan Amount: {format_indian_currency_without_decimal(amount)}

Please evaluate if this loan should proceed based on geographical policy considerations.
Your decision should weigh:
- The maximum allowable loan amount for the specified city.
- Any specific conditions or restrictions associated with the loan purpose.
- General policy guidelines and risk factors.

You MUST respond ONLY with a valid JSON object in the EXACT format below:

{{
    "policy_decision": "APPROVED/CONDITIONAL/REJECTED",
    "max_allowed_amount": numeric_value,
    "conditions": ["list", "of", "conditions"],
    "reasoning": "detailed explanation"
}}

For policy_decision, use ONLY one of these three values: "APPROVED", "CONDITIONAL", or "REJECTED"
Max_allowed_amount must be a number (no commas or currency symbols)
Conditions must be an array of strings
Reasoning must provide a clear explanation for the decision

DO NOT include any text, explanation, or markdown formatting outside of the JSON object.
"""
            try:
                # Print a visual separator to highlight geo policy assessment
                print("\n" + "=" * 50)
                print("🌎 GEO POLICY ASSESSMENT")
                print(f"📍 City: {city} | 🏦 Purpose: {purpose} | 💰 Amount: {format_indian_commas(amount)}")
                
                policy_result = self.llm._call(policy_prompt)
                print(f"💭 Policy Reasoning: Processing geographic eligibility...")
                policy_decision = extract_json_from_string(policy_result)
                
                # Validate that policy_decision has all required fields
                required_fields = ["policy_decision", "max_allowed_amount", "conditions", "reasoning"]
                missing_fields = [field for field in required_fields if field not in policy_decision]
                
                if missing_fields:
                    print(f"⚠️ Missing fields in policy decision: {missing_fields}")
                    # Try to fill in missing fields based on available information
                    if "policy_decision" not in policy_decision:
                        policy_decision["policy_decision"] = "CONDITIONAL"
                    if "max_allowed_amount" not in policy_decision:
                        policy_decision["max_allowed_amount"] = min(float(amount), 1000000)
                    if "conditions" not in policy_decision:
                        policy_decision["conditions"] = ["Standard verification required"]
                    if "reasoning" not in policy_decision:
                        policy_decision["reasoning"] = "Based on standard policy guidelines"
                
                # Ensure policy_decision is one of the valid values
                valid_decisions = ["APPROVED", "CONDITIONAL", "REJECTED"]
                if policy_decision.get("policy_decision") not in valid_decisions:
                    policy_decision["policy_decision"] = "CONDITIONAL"
                
                # Ensure max_allowed_amount is a number
                try:
                    policy_decision["max_allowed_amount"] = float(policy_decision.get("max_allowed_amount", 0))
                except (ValueError, TypeError):
                    policy_decision["max_allowed_amount"] = min(float(amount), 1000000)
                
                # Ensure conditions is a list
                if not isinstance(policy_decision.get("conditions", []), list):
                    if isinstance(policy_decision.get("conditions", ""), str):
                        policy_decision["conditions"] = [policy_decision["conditions"]]
                    else:
                        policy_decision["conditions"] = ["Standard verification required"]
                
                result = {
                    "city": city,
                    "purpose": purpose,
                    "requested_amount": amount,
                    **policy_decision
                }
                # Display the reasoning for better visibility
                print(f"💭 Policy Decision: {policy_decision['policy_decision']}")
                print(f"💭 Reasoning: {policy_decision['reasoning']}")
                print(f"💭 Max Allowed: {format_indian_commas(policy_decision['max_allowed_amount'])}")
                print(f"💭 Conditions: {', '.join(policy_decision['conditions'])}")
                print("=" * 50 + "\n")
                return json.dumps(result, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ Policy decision error: {str(e)}")
                print(f"Raw policy result: {policy_result if 'policy_result' in locals() else 'Not available'}")
                default_policy = {
                    "policy_decision": "CONDITIONAL",
                    "max_allowed_amount": min(float(amount), 1000000),
                    "conditions": ["Standard verification required"],
                    "reasoning": "Based on standard policy guidelines",
                }
                result = {
                    "city": city,
                    "purpose": purpose,
                    "requested_amount": amount,
                    **default_policy
                }
                return json.dumps(result, indent=2, ensure_ascii=False)
                
        except Exception as e:
            return json.dumps({"error": f"Policy validation error: {str(e)}"})

    def run(self, query: str) -> str:
        """Runs the agent's specific task."""
        return self.validate_geo_policy(query)

    def _format_currency(self, amount):
        return format_indian_commas(amount)
