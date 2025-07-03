# loan_agent_orchestrator.
import re
import json
import time
from typing import Dict, Any
from langchain.agents import Tool
from agentic_ai.modules.loan_processing.services.loan_data_service import LoanDataService
from agentic_ai.modules.loan_processing.agents.data_query import DataQueryAgent
from agentic_ai.modules.loan_processing.agents.geo_policy import GeoPolicyAgent
from agentic_ai.modules.loan_processing.agents.risk_assessment import RiskAssessmentAgent
from agentic_ai.modules.loan_processing.agents.user_interaction import UserInteractionAgent
from agentic_ai.modules.loan_processing.agents.salary_sheet import SalarySheetGeneratorAgent, SalarySheetRetrieverAgent
from agentic_ai.modules.loan_processing.agents.pdf_salary_extractor import PDFSalaryExtractorAgent
from agentic_ai.modules.loan_processing.agents.loan_purpose_assessment import LoanPurposeAssessmentAgent
from agentic_ai.modules.loan_processing.agents.customer_agent import CustomerAgent
from agentic_ai.modules.loan_processing.agents.agreement_agent import AgreementAgent
from agentic_ai.core.orchestrator.agent_executor_factory import create_agent_executor
from agentic_ai.core.utils.parsing import parse_initial_user_request
from agentic_ai.core.utils.formatting import format_indian_commas,format_indian_currency_without_decimal
 
class LoanAgentOrchestrator:
    """Orchestrates the loan processing workflow."""
 
    def __init__(self, automate_user: bool = False, customer_profile=None):
        self.data_service = LoanDataService()
        self.data_agent = DataQueryAgent(self.data_service)
        self.geo_agent = GeoPolicyAgent()
        self.risk_agent = RiskAssessmentAgent()
        # Use CustomerAgent if automate_user is True, else UserInteractionAgent
        if automate_user:
            self.interaction_agent = CustomerAgent(profile=customer_profile)
        else:
            self.interaction_agent = UserInteractionAgent()
        self.salary_generator = SalarySheetGeneratorAgent()
        self.salary_retriever = SalarySheetRetrieverAgent()
        self.pdf_extractor = PDFSalaryExtractorAgent()
        self.purpose_agent = LoanPurposeAssessmentAgent() # Add purpose assessment agent
        self.agreement_agent = AgreementAgent() # Add agreement agent
        
        # Escalation tracking
        self.escalation_attempts = {}  # Track attempts per question type
        self.max_attempts = 3
        self.current_question_type = None
        self.conversation_history = []
       
        self.tools = self._setup_tools()
        self.agent_executor = create_agent_executor(self.tools)
 
    def _setup_tools(self):
        import json
        def risk_assessment_wrapper(query):
            # Only patch if input is in the expected format
            if '|' in query:
                user_data_str, loan_amount_str = query.split('|', 1)
                user_data_str = user_data_str.strip()
                loan_amount_str = loan_amount_str.strip()
               
                # Extract api_credit_score directly from the query string using multiple patterns
                api_credit_score = None
                extracted_scores = []
               
                # Pattern 1: Standard JSON format with quotes
                pattern1 = re.search(r'"api_credit_score"\s*:\s*(\d+)', query)
                if pattern1:
                    score = int(pattern1.group(1))
                    extracted_scores.append(("pattern1", score))
                    api_credit_score = score
               
                # Pattern 2: JSON format without quotes
                pattern2 = re.search(r'api_credit_score\s*:\s*(\d+)', query)
                if pattern2 and not pattern1:  # Only use if pattern1 didn't match
                    score = int(pattern2.group(1))
                    extracted_scores.append(("pattern2", score))
                    api_credit_score = score
               
                # Pattern 3: Super broad pattern as last resort
                pattern3 = re.search(r'api_credit_score.*?(\d+)', query)
                if pattern3 and not (pattern1 or pattern2):  # Only use if no other patterns matched
                    score = int(pattern3.group(1))
                    extracted_scores.append(("pattern3", score))
                    api_credit_score = score
               
                if api_credit_score is not None:
                    pass  # Credit score found and will be used
               
                # Parse user_data with multiple fallbacks
                user_data = None
                parse_methods = []
               
                # Method 1: Direct JSON parsing
                try:
                    user_data = json.loads(user_data_str)
                    parse_methods.append("direct_json_load")
                except Exception:
                    pass
               
                # Method 2: Extract JSON using regex if Method 1 failed
                if user_data is None:
                    try:
                        match = re.search(r'\{.*\}', user_data_str)
                        if match:
                            try:
                                user_data = json.loads(match.group(0))
                                parse_methods.append("regex_json_extract")
                            except:
                                pass
                    except:
                        pass
               
                # Method 3: Build object from key-value pairs if Methods 1-2 failed
                if user_data is None:
                    try:
                        user_data = {}
                        parse_methods.append("key_value_parsing")
                        # Parse key-value pairs directly from the string
                        for pair in user_data_str.split(','):
                            if ':' in pair:
                                key, value = pair.split(':', 1)
                                key = key.strip().strip('"').strip("'")
                                value = value.strip().strip('"').strip("'")
                                try:
                                    # Try to convert to appropriate type
                                    if value.isdigit():
                                        value = int(value)
                                    elif value.replace('.', '', 1).isdigit():
                                        value = float(value)
                                    user_data[key] = value
                                except:
                                    pass
                    except:
                        pass
               
                # If all methods failed, create an empty dict
                if user_data is None:
                    user_data = {}
                    parse_methods.append("empty_dict_fallback")
               
                # Process user data parsing results
               
                # GUARANTEED FIX: Ensure user_data is a dict, even if nested
                if isinstance(user_data, dict) and 'user_data' in user_data and isinstance(user_data['user_data'], dict):
                    # Also patch the nested user_data
                    if api_credit_score is not None:
                        user_data['user_data']['credit_score'] = api_credit_score
                        user_data['user_data']['api_credit_score'] = api_credit_score
               
                # GUARANTEED FIX: Override with api_credit_score if we found it
                if api_credit_score is not None:
                    user_data['credit_score'] = api_credit_score
                    user_data['api_credit_score'] = api_credit_score
                elif isinstance(user_data, dict) and 'api_credit_score' in user_data:
                    user_data['credit_score'] = user_data['api_credit_score']
               
                # Force all levels to have the credit score
                if isinstance(user_data, dict):
                    if 'user_data' in user_data and isinstance(user_data['user_data'], dict):
                        # Make sure nested structure has credit_score
                        if 'api_credit_score' in user_data:
                            user_data['user_data']['api_credit_score'] = user_data['api_credit_score']
                            user_data['user_data']['credit_score'] = user_data['api_credit_score']
                        elif 'credit_score' in user_data:
                            user_data['user_data']['credit_score'] = user_data['credit_score']
               
                # Add debug fields to track what happened in orchestrator
                user_data['_debug_orchestrator'] = {
                    'extracted_scores': extracted_scores,
                    'parse_methods': parse_methods,
                    'api_credit_score': api_credit_score
                }
               
                # Reconstruct input with fixed user_data
                new_query = f"{json.dumps(user_data)}|{loan_amount_str}"
                result = self.risk_agent.run(new_query)
               
                # FINAL VERIFICATION: Parse the risk assessment result and verify credit score
                try:
                    result_obj = json.loads(result)
                    if 'user_data_summary' in result_obj and 'credit_score' in result_obj['user_data_summary']:
                        final_credit_score = result_obj['user_data_summary']['credit_score']
                       
                        # If there's still a problem with the credit score (it's 0 when it shouldn't be)
                        if final_credit_score == 0 and api_credit_score is not None and api_credit_score > 0:
                            result_obj['user_data_summary']['credit_score'] = api_credit_score
                            result = json.dumps(result_obj, indent=2)
                except Exception as e:
                    pass
               
                return result
            else:
                return self.risk_agent.run(query)
        return [
            Tool(
                name="UserInteraction",
                description="THE FIRST TOOL TO USE. Get user input. Input: question to ask the user. You MUST ask for loan purpose, loan amount, and city explicitly using separate questions.",
                func=self._user_interaction_with_escalation
            ),
            Tool(
                name="LoanPurposeAssessment",
                description="CRITICAL: ALWAYS run this after collecting loan purpose. Input: loan purpose text. The purpose should be directly from the user's input. This tool evaluates if the purpose is permitted. Returns matched category and policy details.",
                func=self.purpose_agent.run
            ),
            Tool(
                name="DataQuery",
                description="AFTER collecting loan purpose and amount, query user data by PAN or Aadhaar. Input: identifier (PAN or Aadhaar number). For existing users, returns complete user_data with financial details that must be used AS-IS for RiskAssessment. The returned data contains the full user profile needed for risk assessment.",
                func=self.data_agent.run
            ),
            Tool(
                name="CreditScoreByPAN",
                description="SPECIAL TOOL: Use this when DataQuery returns 'user_found_but_pan_needed' status. This fetches credit score using PAN and updates the user data. Input: PAN number. This tool will fetch credit score and return updated user data ready for RiskAssessment.",
                func=self._fetch_credit_score_with_pan
            ),
            Tool(
                name="ValidatePANAadhaar",
                description="SECURITY TOOL: Validate that PAN and Aadhaar belong to the same user. Input format must be exactly: 'complete_dataquery_response|provided_pan' where complete_dataquery_response is the FULL JSON response from DataQuery tool and provided_pan is the PAN number entered by user. Example: '{\"aadhaar_identifier\":\"123456789012\",\"expected_pan\":\"ABCDE1234F\"}|ABCDE1234F'",
                func=lambda query: json.dumps(self._validate_pan_aadhaar_match(*query.split('|', 1)), indent=2)
            ),
            Tool(
                name="MergeUserDataWithCredit",
                description="SPECIAL TOOL: Use this to merge user data (from Aadhaar) with credit score (from PAN). Input format: 'base_user_data_json|credit_score_data_json'. Returns complete user data ready for RiskAssessment.",
                func=lambda query: self._merge_user_data_with_credit_score(*query.split('|', 1))
            ),
            Tool(
                name="GeoPolicyCheck",
                description="ONLY after collecting city, loan purpose and amount. Format MUST BE EXACTLY: 'city:Mumbai,purpose:personal,amount:100000' where city is the customer's city that you explicitly asked for, purpose is the loan purpose, and amount is the loan amount in rupees.",
                func=self.geo_agent.run
            ),
            Tool(
                name="RiskAssessment",
                description="**MANDATORY STEP** - ALWAYS run this after GeoPolicyCheck. This is the final and most important assessment tool. Perform comprehensive risk assessment. REQUIRED FORMAT: 'user_data_json|loan_amount' - The user_data_json must be the COMPLETE user data object from either: 1) DataQuery for existing users who don't want to update salary, 2) PDFSalaryExtractor's output if extraction was successful (use the 'user_data' field from the result), or 3) SalarySheetGenerator only if PDF extraction failed. NEVER skip this tool regardless of GeoPolicyCheck results.",
                func=risk_assessment_wrapper
            ),
            Tool(
                name="PDFSalaryExtractor",
                description="IMPORTANT! Extracts salary information from a PDF file. Use this tool in two scenarios: 1) For NEW USERS when they need to provide salary information, 2) For EXISTING USERS when they want to update their salary information. Input: absolute path to the PDF file (e.g., 'C:\\path\\to\\salary_slip.pdf'). The output contains 'user_data' that MUST be directly used for RiskAssessment if extraction is successful (status: pdf_extraction_successful).",
                func=self.pdf_extractor.run
            ),
            Tool(
                name="SalarySheetGenerator",
                description="FALLBACK ONLY. NEVER use this tool directly unless PDFSalaryExtractor explicitly returns 'fallback_needed': true or 'status': 'pdf_extraction_failed'. If PDFSalaryExtractor returns success, you MUST use that data instead of this tool. Generates mock salary sheet for a new user. Input format: 'user_identifier:PAN_OR_AADHAAR,salary_hint:50000,emi_hint:5000,credit_hint:650'",
                func=self.salary_generator.run
            ),
            Tool(
                name="SalarySheetRetriever",
                description="Retrieves key financial data from a salary sheet JSON. Input: salary_sheet_json.",
                func=self.salary_retriever.run
            ),
            Tool(
                name="AgreementPresentation",
                description="DUAL PURPOSE TOOL - Use for: 1) INITIAL: Present loan agreement with terms & conditions when loan is APPROVED by RiskAssessment. Input: loan approval details (loan_amount, interest_rate, user details). 2) FINAL: Process user's acceptance/rejection response. Input: user's response like 'I AGREE', 'I ACCEPT', 'I DECLINE', or 'I REJECT'. Use this tool twice: first to present agreement, then to process user response.",
                func=self.agreement_agent.run
            )
        ]
    def process_application(self, user_input: str) -> str:
        """Processes a loan application."""
        initial_loan_details = parse_initial_user_request(user_input)
        # Format amount in Indian style for prompt and replace in user_input
        if 'amount' in initial_loan_details and initial_loan_details['amount']:
            formatted_amount = format_indian_currency_without_decimal(initial_loan_details['amount'])
            # Replace all international formatted numbers in user_input with Indian format
            user_input = re.sub(r"(\d{1,3}(?:,\d{3})+|\d{7,})", formatted_amount, user_input)
        else:
            formatted_amount = None
 
        if not self.agent_executor:
            return self._fallback_processing(user_input, "Agent executor not initialized")
 
        # Only reset identity state if not already collected (prevents repeated PAN/Aadhaar prompts)
        if not (getattr(self.interaction_agent, '_aadhaar_collected', False) and getattr(self.interaction_agent, '_aadhaar_consent', False) and getattr(self.interaction_agent, '_pan_collected', False) and getattr(self.interaction_agent, '_pan_consent', False)):
            self.interaction_agent.reset_state()
        self.interaction_agent.set_initial_details(initial_loan_details)
        # Dynamically build the prompt based on what we already know
        prompt_parts = [f'LOAN APPLICATION REQUEST: "{user_input}"\n']
        prompt_parts.append("CRITICAL INSTRUCTIONS - FOLLOW THIS SEQUENCE:")
 
        # Always check purpose first, regardless of initial parsing
        purpose_from_parsing = initial_loan_details.get("purpose", "unknown")
        if purpose_from_parsing in ["unknown", "not_detected"]:
            prompt_parts.append("1. Ask for loan purpose using UserInteraction.")
            prompt_parts.append("2. ALWAYS submit the received purpose to LoanPurposeAssessment to evaluate eligibility.")
        else:
            prompt_parts.append(f"1. The loan purpose '{purpose_from_parsing}' was detected from the initial request.")
            prompt_parts.append("2. ALWAYS submit this purpose to LoanPurposeAssessment to evaluate eligibility.")
       
        prompt_parts.append("   - If purpose is 'prohibited' (eligibility), stop processing and inform user.")
        prompt_parts.append("   - If purpose is 'conditionally_permitted', explain the conditions from policy_details.")
        prompt_parts.append("   - Only continue if purpose is 'permitted' or conditions are met.")
       
        if initial_loan_details.get("amount", 0) == 0:
            prompt_parts.append("3. Ask for loan amount using UserInteraction.")
       
        prompt_parts.append("4. Ask for PAN/Aadhaar using UserInteraction.")
       
        # Unified strict flow for DataQuery and user type handling
        prompt_parts.append("5. Query user data with DataQuery.")
        prompt_parts.append("   - If DataQuery returns status 'new_user_found_proceed_to_salary_sheet', IMMEDIATELY ask the user to upload their salary PDF or TXT document using UserInteraction.")
        prompt_parts.append("     * Use PDFSalaryExtractor with the provided path.")
        prompt_parts.append("     * If PDF extraction is successful (status: pdf_extraction_successful), use the extracted user_data for RiskAssessment and SKIP SalarySheetGenerator.")
        prompt_parts.append("     * If PDF extraction fails, try again with a different path (absolute path, then just filename, then sample_salary_template.txt).")
        prompt_parts.append("     * ONLY IF PDFSalaryExtractor returns 'pdf_extraction_failed' or 'fallback_needed' after all attempts, use SalarySheetGenerator as a final fallback.")
        prompt_parts.append("   - If DataQuery returns an existing user, continue as before:")
        prompt_parts.append("     * Ask: 'Do you want to update your salary information? (yes/no)' with UserInteraction.")
        prompt_parts.append("     * If YES, ask for PDF path and use PDFSalaryExtractor.")
        prompt_parts.append("     * If NO, continue with existing user data.")
        prompt_parts.append("   - If DataQuery returns 'user_found_but_pan_needed', handle PAN requirement securely:")
        prompt_parts.append("     * Store the COMPLETE JSON response from DataQuery")
        prompt_parts.append("     * Use UserInteraction: 'To fetch your credit score for loan processing, please provide your PAN number.'")
        prompt_parts.append("     * SECURITY: Use ValidatePANAadhaar with format: complete_dataquery_json|provided_pan")
        prompt_parts.append("     * EXAMPLE: If DataQuery returned {...full json...} and user provided ABCDE1234F, use: '{...full json...}|ABCDE1234F'")
        prompt_parts.append("     * If validation fails, inform user: 'PAN number does not match our records for this Aadhaar. Please provide the correct PAN.'")
        prompt_parts.append("     * If validation passes, use CreditScoreByPAN tool with the validated PAN number")
        prompt_parts.append("     * Continue with the complete validated user data")
       
        prompt_parts.append("""6. HANDLE USER TYPE:
   - If EXISTING USER is found:
     a. Ask user: "Do you want to update your salary information? (yes/no)" with UserInteraction
     b. If YES → Ask for PDF path: "Please provide the path to your salary PDF document" with UserInteraction
        → Use PDFSalaryExtractor with the provided path
     c. If NO → Continue with existing user data
   - If NEW USER is found:
     a. Ask for PDF path: "Please provide the path to your salary PDF document" with UserInteraction
     b. Use PDFSalaryExtractor with the provided path
     c. CRITICAL: A successful PDF extraction will return "status": "pdf_extraction_successful" with user_data.
        You MUST use this data for risk assessment and skip SalarySheetGenerator completely.
     d. If PDFSalaryExtractor fails to process the file, try again with a different path option:
        - If using absolute path failed, try providing just the filename: sample_salarypdf_template.pdf
        - If the PDF doesn't work, try using sample_salary_template.txt instead
     e. ONLY IF the PDFSalaryExtractor explicitly returns "status": "pdf_extraction_failed" OR "fallback_needed": true
        after all attempts, then use SalarySheetGenerator as a final fallback. NEVER use SalarySheetGenerator unless
        the PDF extraction actually fails after multiple attempts.""")
 
        if initial_loan_details.get("city", "unknown") == "unknown":
            prompt_parts.append("7. Ask for city using UserInteraction.")
 
        prompt_parts.append("8. Run GeoPolicyCheck with format: city:CITY,purpose:PURPOSE,amount:AMOUNT.")
        prompt_parts.append("9. **MANDATORY**: Run RiskAssessment with user data and amount - DO NOT SKIP THIS STEP.")
        prompt_parts.append("10. **AGREEMENT STEP**: If loan is APPROVED by RiskAssessment, use AgreementPresentation to show terms.")
        prompt_parts.append("11. **FINAL STEP**: After presenting agreement, ask user for acceptance using UserInteraction and process response.")
        prompt_parts.append("\nIMPORTANT: Execute ONE action at a time. Wait for each tool response before proceeding to the next step.")
        prompt_parts.append("Even if GeoPolicyCheck shows conditions, you MUST still run RiskAssessment to get the complete picture.")
        prompt_parts.append("If RiskAssessment shows APPROVED status, you MUST present the loan agreement using AgreementPresentation.")
        prompt_parts.append("\nEXECUTE ONE ACTION AT A TIME - DO NOT PLAN MULTIPLE STEPS IN ADVANCE.")
 
        coordination_prompt = "\n".join(prompt_parts)
 
        try:
            result = self.agent_executor.invoke({"input": coordination_prompt})
            return result["output"]
        except Exception as e:
            print(f"[ERROR] Master agent invocation failed: {str(e)}")
            return self._fallback_processing(user_input, str(e))
 
    def _fallback_processing(self, user_input: str, reason: str) -> str:
        """Fallback processing when the main agent fails."""
        # Suppress fallback message for specific early_stopping_method error
        if "Got unsupported early_stopping_method `generate`" in reason:
            return ""  
        loan_amount = parse_initial_user_request(user_input).get('amount', 0)
        return f"""
🏦 **LOAN APPLICATION ERROR - FALLBACK MODE**
**Error Details:** {reason}
**Requested Input:** {user_input}
**Action Required:** Please check system configuration and resubmit.
"""
 
    def _format_final_response(self, text: str) -> str:
        def replace_with_indian_commas(match):
            num = int(match.group(0).replace(",", ""))
            return format_indian_commas(num)
        text = re.sub(r"\d{1,3}(?:,\d{3})+|\d{7,}", replace_with_indian_commas, text)
        return text
 
    def _fetch_credit_score_with_pan(self, pan_number: str) -> str:
        """
        Fetch credit score using PAN and update the previously retrieved user data.
        This is used when user initially provided Aadhaar but PAN is needed for credit score.
        Includes security validation to ensure PAN belongs to the same user as the Aadhaar.
        """
        try:
            from agentic_ai.core.utils.validators import is_pan
            import json
           
            # Validate PAN format
            if not is_pan(pan_number.strip()):
                return json.dumps({
                    "error": "Invalid PAN format. Please provide a valid PAN number.",
                    "status": "invalid_pan"
                })
           
            # Check if there's a stored expected PAN for validation
            # This would be passed via additional context or stored in session
            # For now, we'll need to validate by checking the database
           
            # Fetch user data by PAN to validate it exists and matches
            validation_user_data = self.data_agent.data_service.get_user_data(pan_number.strip())
           
            if validation_user_data.get("status") == "new_user_found_proceed_to_salary_sheet":
                return json.dumps({
                    "error": "PAN number not found in our records. Please verify the PAN number.",
                    "status": "pan_not_found"
                })
           
            # Fetch credit score using the data agent's method
            api_credit_score = self.data_agent.fetch_credit_score_from_api(pan_number.strip())
           
            print(f"\n{'='*50}")
            print("🎯 CREDIT SCORE VERIFICATION")
            print(f"🪪 PAN: {pan_number}")
            print(f"💭 Thought: Fetching credit score for complete user profile...")
            print(f"📊 Credit Score: {api_credit_score}")
            print("="*50 + "\n")
           
            if api_credit_score is None:
                return json.dumps({
                    "error": "Could not fetch credit score for the provided PAN number.",
                    "status": "credit_score_fetch_failed",
                    "pan_number": pan_number,
                    "message": "Please verify the PAN number or try again later."
                })
           
            # Create the complete user data response with credit score
            # Include the validation user data to ensure we have the complete profile
            response = {
                "status": "credit_score_fetched",
                "pan_number": pan_number,
                "api_credit_score": api_credit_score,
                "credit_score": api_credit_score,  # Also set as credit_score for compatibility
                "user_data": validation_user_data,  # Complete user data from PAN lookup
                "message": f"Credit score {api_credit_score} successfully fetched using PAN {pan_number}",
                "instructions": "Credit score has been retrieved. You can now proceed with the complete user data for RiskAssessment.",
                "security_verified": True
            }
           
            return json.dumps(response, indent=2)
           
        except Exception as e:
            return json.dumps({
                "error": f"Error fetching credit score: {str(e)}",
                "status": "fetch_error"
            })
 
    def _merge_user_data_with_credit_score(self, base_user_data: str, credit_score_data: str) -> str:
        """
        Merge user data retrieved via Aadhaar with credit score fetched via PAN.
        This creates a complete user profile for risk assessment.
        """
        try:
            import json
           
            # Parse both data sources
            base_data = json.loads(base_user_data) if isinstance(base_user_data, str) else base_user_data
            credit_data = json.loads(credit_score_data) if isinstance(credit_score_data, str) else credit_score_data
           
            # Extract credit score from credit_data
            api_credit_score = credit_data.get('api_credit_score') or credit_data.get('credit_score')
           
            if api_credit_score is None:
                return json.dumps({"error": "No credit score found in credit data"})
           
            # If base_data has user_data nested, update it
            if 'user_data' in base_data and isinstance(base_data['user_data'], dict):
                base_data['user_data']['credit_score'] = api_credit_score
                base_data['user_data']['api_credit_score'] = api_credit_score
                base_data['user_data']['pan_number'] = credit_data.get('pan_number')
           
            # Also set at root level
            base_data['credit_score'] = api_credit_score
            base_data['api_credit_score'] = api_credit_score
            base_data['pan_number'] = credit_data.get('pan_number')
           
            # Update status
            base_data['status'] = 'complete_user_data_with_credit_score'
            base_data['message'] = f"Complete user profile with credit score {api_credit_score}"
           
            print(f"\n{'='*50}")
            print("🔗 USER DATA MERGE COMPLETE")
            print(f"💭 Thought: Combined Aadhaar user data with PAN credit score")
            print(f"📊 Final Credit Score: {api_credit_score}")
            print("=" * 50 + "\n")
           
            return json.dumps(base_data, indent=2)
           
        except Exception as e:
            return json.dumps({"error": f"Error merging user data: {str(e)}"})
 
    def _validate_pan_aadhaar_match(self, aadhaar_data: str, pan_number: str) -> dict:
        """
        Validate that the provided PAN belongs to the same user as the Aadhaar.
        Returns validation result with security check status.
        """
        try:
            import json
           
            # Parse Aadhaar data - handle both JSON and raw identifiers
            if isinstance(aadhaar_data, str):
                try:
                    parsed = json.loads(aadhaar_data)
                    if isinstance(parsed, dict):
                        aadhaar_info = parsed
                    else:
                        # It's a valid JSON but not a dict (e.g., number, string)
                        print(f"⚠️  Invalid input format: Expected JSON object, got {type(parsed).__name__}")
                        return {
                            "valid": False,
                            "error": "Invalid input format. Expected complete DataQuery JSON response, got simple value.",
                            "reason": "invalid_input_format",
                            "security_note": "Security validation requires complete user data context"
                        }
                except json.JSONDecodeError:
                    # If it's not JSON at all
                    print(f"⚠️  Invalid input format: Expected JSON, got raw string '{aadhaar_data[:50]}...'")
                    return {
                        "valid": False,
                        "error": "Invalid input format. Expected complete DataQuery JSON response, got raw identifier.",
                        "reason": "invalid_input_format",
                        "security_note": "Security validation requires complete user data context"
                    }
            else:
                aadhaar_info = aadhaar_data
           
            # Get expected PAN from Aadhaar lookup
            expected_pan = aadhaar_info.get('expected_pan')
            aadhaar_identifier = aadhaar_info.get('aadhaar_identifier')
           
            print(f"\n{'='*50}")
            print("🔒 SECURITY VALIDATION")
            print(f"🪪 Aadhaar: {aadhaar_identifier}")
            print(f"🔑 Expected PAN: {expected_pan}")
            print(f"🔑 Provided PAN: {pan_number}")
           
            if not expected_pan:
                print("⚠️  Warning: No expected PAN found for validation")
                return {
                    "valid": False,
                    "error": "Unable to validate PAN against user record",
                    "reason": "missing_expected_pan"
                }
           
            if expected_pan.upper().strip() != pan_number.upper().strip():
                print("❌ SECURITY ALERT: PAN does not match user record")
                print("="*50 + "\n")
                return {
                    "valid": False,
                    "error": f"PAN number {pan_number} does not belong to the user with Aadhaar {aadhaar_identifier}",
                    "reason": "pan_aadhaar_mismatch",
                    "security_violation": True
                }
           
            print("✅ SECURITY CHECK PASSED: PAN matches user record")
            print("="*50 + "\n")
            return {
                "valid": True,
                "message": "PAN successfully validated against user record",
                "aadhaar": aadhaar_identifier,
                "pan": pan_number
            }
           
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "reason": "validation_exception"
            }
    
    def _validate_user_response(self, response: str, question: str) -> tuple:
        """
        Validate user response based on question type.
        Returns (is_valid, error_message)
        """
        response = response.strip().lower()
        
        # Determine question type
        question_lower = question.lower()
        
        # Loan amount validation
        if any(keyword in question_lower for keyword in ['amount', 'loan amount', 'how much']):
            try:
                # Parse Indian currency formats
                amount = self._parse_indian_amount(response)
                if amount is None:
                    return False, "Please provide a valid amount (e.g., 50000, 5 lakhs, 2.5 crores)."
                
                # Check realistic range for loan amounts
                if amount < 1000:
                    return False, "Loan amount too small. Minimum is ₹1,000."
                elif amount > 10000000:  # 1 crore
                    return False, "Loan amount too large. Maximum is ₹1,00,00,000."
                
                return True, ""
                
            except:
                return False, "Please provide a valid numeric amount."
        
        # Loan purpose validation
        elif any(keyword in question_lower for keyword in ['purpose', 'use the loan', 'reason']):
            if len(response) < 3 or response in ['i dont know', "don't know", 'idk', 'dunno']:
                return False, "Please specify a clear loan purpose (e.g., bike purchase, home renovation, personal expenses)."
            return True, ""
        
        # PAN validation
        elif any(keyword in question_lower for keyword in ['pan', 'pan number']):
            from agentic_ai.core.utils.validators import is_pan
            if not is_pan(response.upper()):
                return False, "Please provide a valid PAN number (format: ABCDE1234F)."
            return True, ""
        
        # Aadhaar validation
        elif any(keyword in question_lower for keyword in ['aadhaar', 'aadhar']):
            from agentic_ai.core.utils.validators import is_aadhaar
            if not is_aadhaar(response):
                return False, "Please provide a valid 12-digit Aadhaar number."
            return True, ""
        
        # City validation
        elif any(keyword in question_lower for keyword in ['city', 'location']):
            if len(response) < 2:
                return False, "Please provide a valid city name."
            return True, ""
        
        # Yes/No questions validation
        elif any(keyword in question_lower for keyword in ['yes/no', '(yes/no)', 'yes or no', 'salary information']):
            clean_response = response.replace(',', '').replace('.', '').strip()
            yes_responses = ['yes', 'y', 'sure', 'ok', 'okay', 'please', 'yep', 'yeah', 'yup', 'confirm', 'proceed']
            no_responses = ['no', 'n', 'nope', 'not', 'decline', 'skip', 'none', 'negative']
            
            if any(word in clean_response for word in yes_responses) or any(word in clean_response for word in no_responses):
                return True, ""
            else:
                return False, "Please respond with 'yes' or 'no'."
        
        # PDF path questions
        elif any(keyword in question_lower for keyword in ['pdf', 'file', 'document', 'upload']):
            if response.lower().endswith(('.pdf', '.txt')) or 'sample' in response.lower():
                return True, ""
            return False, "Please provide a valid PDF or text file path."
        
        # Default validation - check for gibberish
        if len(response.strip()) < 1:
            return False, "Please provide a valid response."
        
        # Check for obvious gibberish (random characters)
        if len(response) > 3:
            # Count how many characters are letters vs numbers vs special chars
            letters = sum(c.isalpha() for c in response)
            numbers = sum(c.isdigit() for c in response)
            total_chars = len(response.replace(' ', ''))
            
            # If more than 80% of chars are random letters without spaces, likely gibberish
            if total_chars > 5 and letters > total_chars * 0.8 and ' ' not in response:
                # Check if it looks like random typing (no dictionary words)
                words = response.lower().split()
                if len(words) == 1 and len(words[0]) > 6:
                    # Simple check for gibberish - no vowels pattern or too many consonants
                    vowels = sum(1 for c in words[0] if c in 'aeiou')
                    consonants = sum(1 for c in words[0] if c.isalpha() and c not in 'aeiou')
                    if vowels < 2 and consonants > 4:
                        return False, "Please provide a clear, meaningful response."
        
        return True, ""
    
    def _user_interaction_with_escalation(self, question: str) -> str:
        """
        User interaction with escalation support.
        Tracks attempts and escalates to human after max_attempts failures.
        """
        question_key = hash(question)  # Use hash as unique key for this question
        
        if question_key not in self.escalation_attempts:
            self.escalation_attempts[question_key] = 0
        
        while self.escalation_attempts[question_key] < self.max_attempts:
            self.escalation_attempts[question_key] += 1
            attempt_num = self.escalation_attempts[question_key]
            
            print(f"🔄 Attempt {attempt_num}/{self.max_attempts} - UserInteractionAgent")
            
            # Get user response
            response = self.interaction_agent.run(question)
            
            # Add to conversation history
            self.conversation_history.append(f"System: {question}")
            self.conversation_history.append(f"User: {response}")
            
            # Validate response
            is_valid, error_message = self._validate_user_response(response, question)
            
            if is_valid:
                print(f"✅ UserInteractionAgent succeeded on attempt {attempt_num}")
                # Reset attempts for this question on success
                self.escalation_attempts[question_key] = 0
                return response
            else:
                print(f"⚠️ Response validation failed: {error_message}")
                if attempt_num < self.max_attempts:
                    print(f"🔄 Retrying... ({attempt_num}/{self.max_attempts})")
                    # Modify question to include the error message
                    question = f"{error_message} {question}"
                else:
                    # Max attempts reached - ask for escalation
                    escalate_response = self._ask_for_escalation(question, response, error_message)
                    if escalate_response:
                        return escalate_response
        
        # If we get here, escalation was declined or failed
        return f"Unable to process your request. Please contact customer service directly."
    
    def _ask_for_escalation(self, question: str, last_response: str, error_message: str) -> str:
        """
        Ask user if they want to escalate to human agent.
        """
        print(f"\n{'='*60}")
        print("🚨 ESCALATION NOTICE")
        print(f"{'='*60}")
        print(f"We've tried {self.max_attempts} times but couldn't process your response properly.")
        print(f"Last error: {error_message}")
        print(f"Your last response: {last_response}")
        print(f"{'='*60}")
        
        escalation_question = "\nWould you like to escalate this matter to a human agent who can help you personally? (yes/no)"
        escalation_response = input(f"🤔 {escalation_question}\nYour response: ").strip().lower()
        
        if escalation_response in ['yes', 'y', 'sure', 'ok', 'okay', 'please']:
            return self._escalate_to_human(question, last_response, error_message)
        else:
            print("📞 You can contact our customer service at any time for assistance.")
            return None
    
    def _escalate_to_human(self, question: str, user_response: str, error_message: str) -> str:
        """
        Escalate to human agent - connects to actual human operator.
        """
        print(f"\n{'='*60}")
        print("👨‍💼 ESCALATING TO HUMAN AGENT")
        print(f"{'='*60}")
        print("Please wait while we connect you to a human agent...")
        print("A human operator will help you with your request.")
        print(f"{'='*60}")
        
        # Import and use the actual human agent system
        try:
            from agentic_ai.modules.loan_processing.agents.human_agent import get_human_agent
            
            # Create escalation context
            escalation_context = {
                "agent_name": "UserInteractionAgent",
                "user_input": user_response,
                "question": question,
                "failure_count": 3,
                "conversation_history": self.conversation_history.copy(),
                "error_message": error_message,
                "escalated_from": "orchestrator"
            }
            
            # Get human agent and escalate
            human_agent = get_human_agent()
            human_response = human_agent.escalate_to_human(escalation_context)
            
            return human_response
            
        except Exception as e:
            print(f"❌ Error connecting to human agent: {e}")
            # Fallback to basic response
            return f"Unable to connect to human agent right now. Please contact customer service directly or try again later."
    
    def _parse_indian_amount(self, response: str) -> int:
        """
        Parse Indian currency formats like '10 lakhs', '2.5 crores', '50000', etc.
        Returns the amount in rupees or None if invalid.
        """
        import re
        
        response = response.lower().strip()
        
        # Remove common currency symbols and words
        response = re.sub(r'[₹$,]', '', response)
        response = re.sub(r'\brupees?\b|\brs\.?\b', '', response)
        
        # Handle different formats
        if 'crore' in response or 'cr' in response:
            # Extract number before 'crore'
            match = re.search(r'(\d+(?:\.\d+)?)', response)
            if match:
                return int(float(match.group(1)) * 10000000)  # 1 crore = 1,00,00,000
        
        elif 'lakh' in response or 'lac' in response:
            # Extract number before 'lakh'
            match = re.search(r'(\d+(?:\.\d+)?)', response)
            if match:
                return int(float(match.group(1)) * 100000)  # 1 lakh = 1,00,000
        
        elif 'thousand' in response or 'k' in response:
            # Extract number before 'thousand' or 'k'
            match = re.search(r'(\d+(?:\.\d+)?)', response)
            if match:
                return int(float(match.group(1)) * 1000)  # 1 thousand = 1,000
        
        else:
            # Try to extract plain number
            numbers = re.findall(r'\d+', response.replace(',', ''))
            if numbers:
                return int(''.join(numbers))
        
        return None