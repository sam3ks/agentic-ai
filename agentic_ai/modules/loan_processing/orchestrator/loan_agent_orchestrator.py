# loan_agent_orchestrator.
import re
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
from agentic_ai.modules.loan_processing.agents.offer_refinement_agent import OfferRefinementAgent # Import the new agent

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
        self.offer_refinement_agent = OfferRefinementAgent() # Instantiate OfferRefinementAgent
       
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
                func=self.interaction_agent.run
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
                name="OfferRefinement",
                description="**MANDATORY STEP** - ALWAYS run this immediately after RiskAssessment before presenting any agreement. This tool analyzes the risk assessment output to suggest relevant upsell/cross-sell offers. Input: Complete JSON output from RiskAssessmentAgent. Returns JSON string with suggested offers and reasoning. DO NOT SKIP THIS TOOL.",
                func=self.offer_refinement_agent.run
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
       
        # Reset and prime the UserInteractionAgent
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
        prompt_parts.append("5. Query user data with DataQuery.")
       
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
        prompt_parts.append("10. **MANDATORY**: After RiskAssessment, run OfferRefinement with the JSON output from RiskAssessment - DO NOT SKIP THIS STEP.")
        prompt_parts.append("11. **AGREEMENT STEP**: After OfferRefinement, if loan is APPROVED by RiskAssessment, use AgreementPresentation to show terms.")
        prompt_parts.append("12. **FINAL STEP**: After presenting agreement, ask user for acceptance using UserInteraction and process response.")
        prompt_parts.append("\nIMPORTANT: Execute ONE action at a time. Wait for each tool response before proceeding to the next step.")
        prompt_parts.append("Even if GeoPolicyCheck shows conditions, you MUST still run RiskAssessment to get the complete picture.")
        prompt_parts.append("After RiskAssessment, you MUST run OfferRefinement before presenting any loan agreement.")
        prompt_parts.append("If RiskAssessment shows APPROVED status, you MUST first run OfferRefinement, then present the loan agreement using AgreementPresentation.")
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

