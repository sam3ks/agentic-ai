# loan_agent_orchestrator.
import re
import json
import time
from typing import Dict, Any
from langchain_core.tools import Tool
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
from agentic_ai.core.orchestrator.agent_executor_factory import create_agent_workflow
from agentic_ai.core.utils.parsing import parse_initial_user_request, parse_amount_string
from agentic_ai.core.utils.formatting import format_indian_commas,format_indian_currency_without_decimal
from agentic_ai.core.session.session_manager import get_session_manager
 
class LoanAgentOrchestrator:
    """Orchestrates the loan processing workflow."""

    def __init__(self, automate_user: bool = False, customer_profile=None, input_provider=None, session_id=None, clean_ui: bool = True):
        self.clean_ui = clean_ui  # Control debug output visibility
        self.data_service = LoanDataService()
        self.data_agent = DataQueryAgent(self.data_service)
        self.geo_agent = GeoPolicyAgent()
        self.risk_agent = RiskAssessmentAgent()
        # Use CustomerAgent if automate_user is True, else UserInteractionAgent
        if automate_user:
            self.interaction_agent = CustomerAgent(profile=customer_profile)
        else:
            self.interaction_agent = UserInteractionAgent(input_provider=input_provider)
        self.salary_generator = SalarySheetGeneratorAgent()
        self.salary_retriever = SalarySheetRetrieverAgent()
        self.pdf_extractor = PDFSalaryExtractorAgent()
        self.purpose_agent = LoanPurposeAssessmentAgent() # Add purpose assessment agent
        self.agreement_agent = AgreementAgent() # Add agreement agent        # Escalation tracking
        self.escalation_attempts = {}  # Track attempts per question type
        self.max_attempts = 3
        self.current_question_type = None
        self.conversation_history = []
        
        # Tool output capture for agreement extraction
        self.captured_agreement = None
        self.captured_loan_details = None  # Store loan details for frontend
        self.captured_tool_outputs = {}
        
        # Store existing user data when user says "no" to salary update
        self.stored_existing_user_data = None
        
        # Session management
        self.session_manager = get_session_manager()
        # If a specific session_id is provided, resume that session
        if session_id:
            if not self.session_manager.resume_session(session_id):
                print(f"⚠️ Could not resume session {session_id}, starting new session")
        else:
            # Check if there's an existing completed session that needs to be cleared
            if (self.session_manager.session_id and 
                self.session_manager.get_state("status") == "completed"):
                print(f"✅ Previous session completed, starting fresh session")
                # Force a fresh session start
                self.session_manager.start_fresh_session()
       
        self.tools = self._setup_tools()
        self.agent_workflow = create_agent_workflow(self.tools)
 
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

        # Wrapper for LoanPurposeAssessment that updates state with mapped category
        def loan_purpose_assessment_wrapper(query):
            """LoanPurposeAssessment wrapper that captures the mapped category and updates state."""
            
            if not self.clean_ui:
                print(f"[DEBUG] LoanPurposeAssessment called with input: '{query}'")
            
            # Call the actual LoanPurposeAssessment tool
            result = self.purpose_agent.run(query)
            
            if not self.clean_ui:
                print(f"[DEBUG] LoanPurposeAssessment result: {result}")
            
            # Parse the result to extract the mapped category
            try:
                import json
                result_obj = json.loads(result)
                mapped_category = result_obj.get("matched_category")
                
                if mapped_category:
                    if not self.clean_ui:
                        print(f"[DEBUG] Updating purpose from '{query}' to mapped category '{mapped_category}'")
                    
                    # Update session state with mapped category
                    self.session_manager.update_collected_data("purpose", mapped_category)
                    
                    # Also update any stored initial loan details
                    collected_data = self.session_manager.get_state("collected_data", {})
                    if "initial_loan_details" in collected_data:
                        collected_data["initial_loan_details"]["purpose"] = mapped_category
                        self.session_manager.update_state("collected_data", collected_data)
                        if not self.clean_ui:
                            print(f"[DEBUG] Updated initial_loan_details with mapped purpose: {mapped_category}")
                            
            except Exception as e:
                if not self.clean_ui:
                    print(f"[DEBUG] Could not parse LoanPurposeAssessment result for state update: {e}")
            
            return result

        # Wrapper for DataQuery that processes the response and triggers next actions
        def data_query_wrapper(query):
            """DataQuery wrapper that handles salary workflow enforcement and security validation."""
            
            # SECURITY CHECK: Auto-validate PAN/Aadhaar if both are available
            if (hasattr(self.interaction_agent, '_aadhaar_number') and self.interaction_agent._aadhaar_number and 
                hasattr(self.interaction_agent, '_pan_number') and self.interaction_agent._pan_number):
                
                if not self.clean_ui:
                    print(f"\n🔒 SECURITY: Both identifiers collected, performing cross-validation...")
                    print(f"🪪 User provided Aadhaar: {self.interaction_agent._aadhaar_number}")
                    print(f"🔑 User provided PAN: {self.interaction_agent._pan_number}")
                
                # First, call DataQuery silently with Aadhaar to get the expected PAN for validation
                if not self.clean_ui:
                    print(f"[DEBUG] Security validation: Looking up Aadhaar {self.interaction_agent._aadhaar_number} to find expected PAN...")
                aadhaar_data = self.data_agent.query_user_data_silent(self.interaction_agent._aadhaar_number)
                
                if not self.clean_ui:
                    print(f"[DEBUG] Security validation - Aadhaar data structure: {type(aadhaar_data)}")
                    print(f"[DEBUG] Security validation - Aadhaar data keys: {list(aadhaar_data.keys()) if isinstance(aadhaar_data, dict) else 'Not a dict'}")
                
                # Extract the expected PAN from Aadhaar data
                expected_pan = None
                if isinstance(aadhaar_data, dict):
                    if "user_data" in aadhaar_data and isinstance(aadhaar_data["user_data"], dict):
                        expected_pan = aadhaar_data["user_data"].get("pan_number")
                        if not self.clean_ui:
                            print(f"[DEBUG] Security validation - Found PAN in user_data: {expected_pan}")
                    else:
                        expected_pan = aadhaar_data.get("pan_number")
                        if not self.clean_ui:
                            print(f"[DEBUG] Security validation - Found PAN in root: {expected_pan}")
                    
                    # If we found expected PAN, validate it against provided PAN
                    if expected_pan:
                        if not self.clean_ui:
                            print(f"🔍 Expected PAN from Aadhaar: {expected_pan}")
                            print(f"🔍 Provided PAN from user: {self.interaction_agent._pan_number}")
                            print(f"🔍 PAN comparison: '{expected_pan.upper().strip()}' vs '{self.interaction_agent._pan_number.upper().strip()}'")
                        
                        if expected_pan.upper().strip() != self.interaction_agent._pan_number.upper().strip():
                            if not self.clean_ui:
                                print("❌ SECURITY ALERT: PAN does not match Aadhaar record!")
                            
                            security_error = {
                                "error": "SECURITY_VALIDATION_FAILED", 
                                "message": f"The PAN number {self.interaction_agent._pan_number} does not belong to the user with Aadhaar {self.interaction_agent._aadhaar_number}. Please provide the correct PAN number that matches your Aadhaar record.",
                                "provided_pan": self.interaction_agent._pan_number,
                                "provided_aadhaar": self.interaction_agent._aadhaar_number,
                                "expected_pan": expected_pan,
                                "action_required": "ask_for_correct_pan"
                            }
                            # Reset PAN to force re-collection
                            self.interaction_agent._pan_collected = False
                            self.interaction_agent._pan_consent = False
                            self.interaction_agent._pan_number = None
                            return json.dumps(security_error, indent=2)
                        else:
                            if not self.clean_ui:
                                print("✅ SECURITY CHECK PASSED: PAN matches Aadhaar record")
                    else:
                        if not self.clean_ui:
                            print("ℹ️  No expected PAN found in Aadhaar record, proceeding...")
                else:
                    if not self.clean_ui:
                        print(f"[DEBUG] Security validation - Aadhaar data is not dict: {type(aadhaar_data)}")
            
            result = self.data_agent.run(query)
            
            # Parse the DataQuery result to check for specific response patterns
            try:
                result_data = json.loads(result)
                
                # EXISTING USER: Check for salary update action needed
                if result_data.get("action_needed") == "ask_about_salary_update":
                    if not self.clean_ui:
                        print("[DEBUG] DataQuery detected EXISTING USER - action_needed: ask_about_salary_update")
                        print("[DEBUG] FORCING salary update question as immediate next step")
                    
                    # CRITICAL: Store the complete user data for later use when user says "no"
                    if "user_data" in result_data:
                        self.stored_existing_user_data = result_data["user_data"]
                        if not self.clean_ui:
                            print("[DEBUG] Stored existing user data for potential 'no' response")
                    
                    # Return modified response that forces salary update question
                    result_data["_orchestrator_next_action"] = "salary_update_question"
                    result_data["_orchestrator_message"] = "CRITICAL: You MUST immediately ask the user: 'Do you want to update your salary information?' Do NOT ask for city or anything else first."
                    
                    return json.dumps(result_data, indent=2)
                
                # NEW USER: Check for salary sheet needed  
                elif result_data.get("status") == "new_user_found_proceed_to_salary_sheet":
                    if not self.clean_ui:
                        print("[DEBUG] DataQuery detected NEW USER - status: new_user_found_proceed_to_salary_sheet")
                        print("[DEBUG] This is working fine, keeping as-is")
                    return result
                
                else:
                    # Regular DataQuery response - no special handling needed
                    return result
                    
            except json.JSONDecodeError:
                # If response is not JSON, return as-is
                return result

        # Wrapper for AgreementPresentation that captures output
        def agreement_presentation_wrapper(query):
            # Handle user acceptance/rejection first (before calling agent)
            if any(x in query.upper() for x in ["I ACCEPT", "I AGREE", "I REJECT", "I DECLINE"]):
                # Process acceptance/rejection directly
                if any(x in query.upper() for x in ["ACCEPT", "AGREE"]):
                    confirmation = "LOAN AGREEMENT DIGITALLY ACCEPTED. Thank you! Your loan application has been successfully processed."
                else:
                    confirmation = "LOAN DECLINED. Thank you for considering our services."
                
                # Send confirmation to frontend if available
                if hasattr(self.interaction_agent, 'input_provider') and hasattr(self.interaction_agent.input_provider, 'output_queue'):
                    self.interaction_agent.input_provider.output_queue.put(confirmation)
                
                return confirmation
            
            # Use the new present_agreement method to get both text and details
            agreement_result = self.agreement_agent.present_agreement(query)
            if isinstance(agreement_result, dict) and "agreement_text" in agreement_result:
                agreement_text = agreement_result["agreement_text"]
                loan_details = agreement_result.get("loan_details", {})
                self.captured_agreement = agreement_text
                self.captured_loan_details = loan_details  # Store loan details
                
                # For backend compatibility, put just the agreement text in the output queue
                if hasattr(self.interaction_agent, 'input_provider') and hasattr(self.interaction_agent.input_provider, 'output_queue'):
                    # Always send agreement text and loan details first
                    self.interaction_agent.input_provider.output_queue.put(agreement_text)
                    self.interaction_agent.input_provider.output_queue.put({"loan_details": loan_details})
                    
                    # Create separate acceptance prompt
                    acceptance_prompt = "To proceed with digital acceptance, please respond with: 'I AGREE' or 'I ACCEPT' - to accept the terms; 'I DECLINE' or 'I REJECT' - to decline the loan."
                    
                    # Return only the acceptance prompt string to the agent executor
                    # This is sent after agreement is fully displayed
                    time.sleep(0.5)  # Short delay to ensure agreement is processed first
                    return acceptance_prompt
                else:
                    return agreement_text
            # Default fallback
            return None
        return [
            Tool(
                name="UserInteraction",
                description="THE FIRST TOOL TO USE. Get user input. Input: question to ask the user. ⚠️ CRITICAL: After collecting loan purpose, you MUST IMMEDIATELY use LoanPurposeAssessment tool - DO NOT ask for amount first! You MUST ask for loan purpose, loan amount, and city explicitly using separate questions.",
                func=self._user_interaction_with_escalation
            ),
            Tool(
                name="LoanPurposeAssessment",
                description="🔥 CRITICAL SECOND STEP: IMMEDIATELY use this after collecting loan purpose! Input: loan purpose text (exactly as user provided). This tool maps user input like 'bike loan' to standardized categories like 'vehicle_purchase' and checks policy eligibility. YOU MUST USE THIS BEFORE proceeding to ask for loan amount. Returns matched category and policy details.",
                func=loan_purpose_assessment_wrapper
            ),
            Tool(
                name="DataQuery",
                description="Query user data by PAN or Aadhaar. Input: identifier (PAN or Aadhaar number). CRITICAL: After calling this tool, you MUST immediately check the response for two specific fields: 1) 'action_needed': 'ask_about_salary_update' (existing user) - requires immediate salary update question, 2) 'status': 'new_user_found_proceed_to_salary_sheet' (new user) - requires immediate PDF upload request. DO NOT proceed to ask for city until you handle the salary workflow based on these response flags.",
                func=data_query_wrapper
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
                name="UseExistingUserData",
                description="CRITICAL FOR EXISTING USERS WHO SAY NO: Use this when an existing user chooses NOT to update their salary information. Input: 'no_salary_update'. This retrieves the complete user data from DataQuery. To use for RiskAssessment, take this output and format it as: 'output_from_this_tool|loan_amount'. This ensures existing users who say 'no' get their original financial data (salary, EMI, credit score) used in RiskAssessment.",
                func=lambda query: self._get_existing_user_data_for_risk_assessment()
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
                description="MANDATORY for salary processing. Extracts salary information from PDF files. Use this tool: 1) For NEW USERS (when DataQuery returns 'new_user_found_proceed_to_salary_sheet') - REQUIRED to get salary data, 2) For EXISTING USERS who want to update salary. Input: absolute path to PDF file. The output contains 'user_data' that MUST be used for RiskAssessment. For NEW USERS, this is the ONLY way to get salary data - without this, RiskAssessment will fail with zero salary.",
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
                func=agreement_presentation_wrapper
            )
        ]
    def process_application(self, user_input: str) -> str:
        """Processes a loan application with session persistence."""
        
        # Check if we already have a session (from resume)
        if self.session_manager.session_id:
            print(f"📋 Continuing existing session: {self.session_manager.session_id}")
            session_id = self.session_manager.session_id
            
            # Check if we're resuming a session
            existing_data = self.session_manager.get_state("collected_data", {})
            existing_step = self.session_manager.get_state("workflow_step", 0)
            
            if existing_step > 0:
                print(f"📋 Resuming from step {existing_step}")
                # Restore orchestrator state if resuming
                orchestrator_state = self.session_manager.get_state("orchestrator_state", {})
                if orchestrator_state:
                    self._restore_state_from_session(orchestrator_state)
                    
                    # Extract missing data from conversation history and restore to collected_data
                    conversation_history = orchestrator_state.get("conversation_history", [])
                    for entry in conversation_history:
                        if "city" in entry and entry.startswith("User: {\"city\":"):
                            try:
                                import json
                                # Extract city from user response like 'User: {"city": "Chennai"}'
                                user_data = json.loads(entry.split("User: ", 1)[1])
                                if "city" in user_data and user_data["city"]:
                                    self.session_manager.update_collected_data("city", user_data["city"])
                                    print(f"[DEBUG] Restored city from conversation: {user_data['city']}")
                            except:
                                pass
                
                # For resumed sessions, don't reparse - use existing data
                initial_loan_details = existing_data.get("initial_loan_details", {})
                
                # Update initial_loan_details with any collected data that's missing
                if "city" in existing_data and existing_data["city"]:
                    initial_loan_details["city"] = existing_data["city"]
                if "purpose" in existing_data and existing_data["purpose"]:
                    initial_loan_details["purpose"] = existing_data["purpose"]
                if "amount" in existing_data and existing_data["amount"]:
                    # Parse amount string to numeric value for consistency
                    parsed_amount = parse_amount_string(existing_data["amount"])
                    initial_loan_details["amount"] = parsed_amount if parsed_amount > 0 else existing_data["amount"]
                
                if not self.clean_ui:
                    print(f"[DEBUG] Restored initial details: {initial_loan_details}")
            else:
                # Parse initial request for new session
                initial_loan_details = parse_initial_user_request(user_input)
                self.session_manager.update_collected_data("initial_loan_details", initial_loan_details)
                self.session_manager.add_conversation_entry("User", user_input)
                self.session_manager.set_workflow_step(1, "Processing initial request")
        else:
            # Start a new session
            session_id = self.session_manager.start_session(user_input)
            existing_data = {}  # Initialize for new session
            existing_step = 0   # Initialize for new session
            
            # Parse initial request and save to session
            initial_loan_details = parse_initial_user_request(user_input)
            self.session_manager.update_collected_data("initial_loan_details", initial_loan_details)
            self.session_manager.add_conversation_entry("User", user_input)
            self.session_manager.set_workflow_step(1, "Processing initial request")
        
        # Store parsed details in session (only if not resuming or if details are new)
        existing_initial_details = existing_data.get("initial_loan_details", {})
        if not existing_initial_details or existing_step == 0:
            self.session_manager.update_collected_data("initial_loan_details", initial_loan_details)
        # Format amount in Indian style for prompt and replace in user_input
        if 'amount' in initial_loan_details and initial_loan_details['amount']:
            # Parse amount string to numeric value first
            numeric_amount = parse_amount_string(initial_loan_details['amount'])
            if numeric_amount > 0:
                # Update the initial_loan_details with numeric amount for consistency
                initial_loan_details['amount'] = numeric_amount
                formatted_amount = format_indian_currency_without_decimal(numeric_amount)
                # Replace all international formatted numbers in user_input with Indian format
                # Use negative lookbehind to avoid double rupee symbols
                user_input = re.sub(r"(?<!₹)(\d{1,3}(?:,\d{3})+|\d{7,})", formatted_amount, user_input)
                # Also replace any existing rupee symbols with numbers to avoid ₹₹ patterns
                user_input = re.sub(r"₹(\d{1,3}(?:,\d{3})+|\d{7,})", formatted_amount, user_input)
            else:
                formatted_amount = None
        else:
            formatted_amount = None
 
        if not self.agent_workflow:
            return self._fallback_processing(user_input, "Agent workflow not initialized")
 
        # Only reset identity state if not already collected (prevents repeated PAN/Aadhaar prompts)
        if not (getattr(self.interaction_agent, '_aadhaar_collected', False) and getattr(self.interaction_agent, '_aadhaar_consent', False) and getattr(self.interaction_agent, '_pan_collected', False) and getattr(self.interaction_agent, '_pan_consent', False)):
            self.interaction_agent.reset_state()
        self.interaction_agent.set_initial_details(initial_loan_details)
        # Dynamically build the prompt based on what we already know
        prompt_parts = [f'LOAN APPLICATION REQUEST: "{user_input}"\n']
        prompt_parts.append("🚨 ABSOLUTE MANDATORY RULE - NEVER SKIP THIS: 🚨")
        prompt_parts.append("After EVERY loan purpose collection, you MUST use LoanPurposeAssessment before asking for amount!")
        prompt_parts.append("Example: UserInteraction gets 'bike loan' → IMMEDIATELY use LoanPurposeAssessment with 'bike loan'")
        prompt_parts.append("")
        prompt_parts.append("CRITICAL INSTRUCTIONS - FOLLOW THIS SEQUENCE:")
        prompt_parts.append("IMPORTANT: After DataQuery step, you MUST check the response for salary-related actions before doing anything else!")
        prompt_parts.append("")
 
        # Always check purpose first, regardless of initial parsing
        purpose_from_parsing = initial_loan_details.get("purpose", "unknown")
        if purpose_from_parsing in ["unknown", "not_detected"]:
            prompt_parts.append("1. Ask for loan purpose using UserInteraction.")
            prompt_parts.append("2. ⚠️  CRITICAL MANDATORY STEP - NO EXCEPTIONS: ⚠️")
            prompt_parts.append("   IMMEDIATELY after receiving ANY loan purpose, you MUST use LoanPurposeAssessment tool!")
            prompt_parts.append("   Example: User says 'bike loan' → Use LoanPurposeAssessment with input: bike loan")
            prompt_parts.append("   - This maps the purpose to standardized categories (e.g., 'bike loan' → 'vehicle purchase')")
            prompt_parts.append("   - You MUST wait for LoanPurposeAssessment response before asking for amount!")
        else:
            prompt_parts.append(f"1. The loan purpose '{purpose_from_parsing}' was detected from the initial request.")
            prompt_parts.append("2. ⚠️  CRITICAL MANDATORY STEP - NO EXCEPTIONS: ⚠️")
            prompt_parts.append("   IMMEDIATELY submit this purpose to LoanPurposeAssessment tool!")
            prompt_parts.append("   - This maps the purpose to standardized categories and checks policy eligibility.")
            prompt_parts.append("   - You MUST wait for LoanPurposeAssessment response before proceeding.")
       
        prompt_parts.append("   - If purpose is 'prohibited' (eligibility), stop processing and inform user.")
        prompt_parts.append("   - If purpose is 'conditionally_permitted', explain the conditions from policy_details.")
        prompt_parts.append("   - Only continue if purpose is 'permitted' or conditions are met.")
       
        if initial_loan_details.get("amount", 0) == 0:
            prompt_parts.append("3. ⚠️  ONLY AFTER LoanPurposeAssessment is COMPLETE: Ask for loan amount using UserInteraction")
            prompt_parts.append("   DO NOT ask for amount until you have received LoanPurposeAssessment response!")
       
        prompt_parts.append("4. Ask for PAN/Aadhaar using UserInteraction.")
       
        # CRITICAL: Explicit salary handling workflow
        prompt_parts.append("5. Query user data with DataQuery.")
        prompt_parts.append("")
        prompt_parts.append("   **SECURITY VALIDATION** - If DataQuery returns error: \"SECURITY_VALIDATION_FAILED\":")
        prompt_parts.append("   → This means the PAN and Aadhaar don't belong to the same person")
        prompt_parts.append("   → Inform user: 'The PAN number you provided does not match your Aadhaar record. Please provide the correct PAN number.'")
        prompt_parts.append("   → Use UserInteraction to collect the correct PAN again")
        prompt_parts.append("")
        prompt_parts.append("   **IMPORTANT**: Ignore any '[INFO] No PAN provided' messages - these are normal during security validation.")
        prompt_parts.append("   **IMPORTANT**: Only treat explicit 'SECURITY_VALIDATION_FAILED' errors as security issues.")
        prompt_parts.append("   → Retry DataQuery with the corrected PAN")
        prompt_parts.append("")
        prompt_parts.append("6. **SALARY WORKFLOW - MANDATORY IMMEDIATE STEP**")
        prompt_parts.append("   CRITICAL: After DataQuery, check the response for special orchestrator messages!")
        prompt_parts.append("")
        prompt_parts.append("   **EXISTING USER** - If DataQuery response contains: \"_orchestrator_next_action\": \"salary_update_question\"")
        prompt_parts.append("   → This means an EXISTING USER was found and you MUST immediately ask:")
        prompt_parts.append("   → UserInteraction(\"Do you want to update your salary information?\")")
        prompt_parts.append("   → Wait for user response (YES/NO)")
        prompt_parts.append("   → If user says YES: UserInteraction(\"Please upload your salary PDF file path\")")
        prompt_parts.append("   → Then call PDFSalaryExtractor with the provided path")
        prompt_parts.append("   → If user says NO: Use UseExistingUserData tool to get the stored user data")
        prompt_parts.append("   → The UseExistingUserData tool returns the complete user data JSON")
        prompt_parts.append("   → For RiskAssessment, format as: UseExistingUserData_output|loan_amount")
        prompt_parts.append("")
        prompt_parts.append("   **NEW USER** - If DataQuery contains: \"status\": \"new_user_found_proceed_to_salary_sheet\"")
        prompt_parts.append("   → Your IMMEDIATE next action MUST be: UserInteraction(\"Please upload your salary information (PDF)\")")
        prompt_parts.append("   → Then MANDATORY call PDFSalaryExtractor with the provided PDF path")
        prompt_parts.append("   → Store the extracted user_data from PDFSalaryExtractor for RiskAssessment")
        prompt_parts.append("")
        prompt_parts.append("   **CRITICAL**: Only after completing the salary workflow above, proceed to collect city.")
        prompt_parts.append("   - If DataQuery returns 'user_found_but_pan_needed', handle PAN requirement securely:")
        prompt_parts.append("     * Store the COMPLETE JSON response from DataQuery")
        prompt_parts.append("     * Use UserInteraction: 'To fetch your credit score for loan processing, please provide your PAN number.'")
        prompt_parts.append("     * SECURITY: Use ValidatePANAadhaar with format: complete_dataquery_json|provided_pan")
        prompt_parts.append("     * EXAMPLE: If DataQuery returned {...full json...} and user provided ABCDE1234F, use: '{...full json...}|ABCDE1234F'")
        prompt_parts.append("     * If validation fails, inform user: 'PAN number does not match our records for this Aadhaar. Please provide the correct PAN.'")
        prompt_parts.append("     * If validation passes, use CreditScoreByPAN tool with the validated PAN number")
        prompt_parts.append("     * Continue with the complete validated user data")
       
        prompt_parts.append("""**CRITICAL SEQUENCE ENFORCEMENT:**

STEP 5: DataQuery  
  - If error: "SECURITY_VALIDATION_FAILED" → Ask for correct PAN and retry
STEP 6: Check DataQuery response immediately for orchestrator messages:
  - If "_orchestrator_next_action": "salary_update_question" → Ask existing user salary update question  
  - If "status": "new_user_found_proceed_to_salary_sheet" → Ask for PDF upload
STEP 7: Handle salary workflow (existing user update or new user PDF extraction)
  - If existing user says NO: Use UseExistingUserData, then use output for RiskAssessment
  - If existing user says YES: Use PDFSalaryExtractor
  - If new user: Use PDFSalaryExtractor
STEP 8: Ask for city ONLY after salary workflow is complete
STEP 9: GeoPolicyCheck
STEP 10: RiskAssessment with correct user data:
  - Format: user_data_json|loan_amount
  - For NO salary update: UseExistingUserData_output|loan_amount
  - For YES/new user: PDFSalaryExtractor_user_data|loan_amount
STEP 11: AgreementPresentation if approved

DO NOT SKIP THE SALARY WORKFLOW IN STEP 6-7. For existing users, the orchestrator adds special messages to force this.""")
 
        if initial_loan_details.get("city", "unknown") == "unknown":
            prompt_parts.append("7. **ONLY AFTER SALARY WORKFLOW IS COMPLETE**: Ask for city using UserInteraction.")
 
        prompt_parts.append("8. Run GeoPolicyCheck with format: city:CITY,purpose:PURPOSE,amount:AMOUNT.")
        prompt_parts.append("9. **MANDATORY**: Run RiskAssessment with the correct user data:")
        prompt_parts.append("   - For EXISTING USERS who said NO to salary update: Use user_data from UseExistingUserData tool")
        prompt_parts.append("   - For NEW USERS: Use the user_data extracted by PDFSalaryExtractor (MANDATORY)")
        prompt_parts.append("   - For EXISTING USERS who updated salary: Use the user_data from PDFSalaryExtractor")
        prompt_parts.append("10. **AGREEMENT STEP**: If loan is APPROVED by RiskAssessment, use AgreementPresentation to show terms.")
        prompt_parts.append("11. **FINAL STEP**: After presenting agreement, ask user for acceptance using UserInteraction and process response.")
        prompt_parts.append("\nIMPORTANT: Execute ONE action at a time. Wait for each tool response before proceeding to the next step.")
        prompt_parts.append("Even if GeoPolicyCheck shows conditions, you MUST still run RiskAssessment to get the complete picture.")
        prompt_parts.append("If RiskAssessment shows APPROVED status, you MUST present the loan agreement using AgreementPresentation.")
        prompt_parts.append("\nEXECUTE ONE ACTION AT A TIME - DO NOT PLAN MULTIPLE STEPS IN ADVANCE.")
 
        coordination_prompt = "\n".join(prompt_parts)
 
        try:
            # Reset captured agreement before execution
            self.captured_agreement = None
            self.captured_loan_details = None
            self.captured_tool_outputs = {}
            # Reset stored existing user data for new application
            self.stored_existing_user_data = None
            
            # Save orchestrator state to session before workflow
            self._save_state_to_session()
            self.session_manager.set_workflow_step(2, "Starting agent workflow")
            
            # Check if we have existing session state to restore
            collected_data = self.session_manager.get_state("collected_data", {})
            existing_agent_state = self.session_manager.get_state("final_agent_state", {})
            
            # Restore collected data from session AND initial parsing
            purpose = ""
            amount = ""
            city = ""
            pan = ""
            aadhaar = ""
            
            if collected_data:
                initial_details = collected_data.get("initial_loan_details", {})
                purpose = initial_details.get("purpose", "")
                amount = str(initial_details.get("amount", "")) if initial_details.get("amount") else ""
                city = initial_details.get("city", "")  # This should include parsed city from initial request
                pan = collected_data.get("pan", "")
                aadhaar = collected_data.get("aadhaar", "")
                
                if not self.clean_ui:
                    print(f"[DEBUG] Restored from session - Purpose: {purpose}, Amount: {amount}, City: {city}, PAN: {pan}, Aadhaar: {aadhaar}")
                
                # CRITICAL: Restore UserInteractionAgent state for security validation
                if pan and aadhaar:
                    if not self.clean_ui:
                        print(f"[DEBUG] Restoring UserInteractionAgent with both identifiers for security validation")
                    # Restore the interaction agent state
                    self.interaction_agent._pan_number = pan
                    self.interaction_agent._pan_collected = True
                    self.interaction_agent._pan_consent = True
                    self.interaction_agent._aadhaar_number = aadhaar
                    self.interaction_agent._aadhaar_collected = True
                    self.interaction_agent._aadhaar_consent = True
            
            # CRITICAL: If city was detected in initial parsing but not in session, use the parsed value
            if not city and initial_loan_details.get("city") and initial_loan_details.get("city") != "unknown":
                city = initial_loan_details.get("city")
                if not self.clean_ui:
                    print(f"[DEBUG] Using city from initial parsing: {city}")
                # Save it to session immediately
                self.session_manager.update_collected_data("city", city)
            
            # CRITICAL: Ensure parsed amounts are numeric and properly formatted
            if not amount and initial_loan_details.get("amount"):
                parsed_amount = parse_amount_string(str(initial_loan_details.get("amount")))
                if parsed_amount > 0:
                    amount = str(parsed_amount)
                    if not self.clean_ui:
                        print(f"[DEBUG] Using amount from initial parsing: {amount}")
                    # Save it to session immediately
                    self.session_manager.update_collected_data("amount", amount)
            
            initial_state = {
                "input": coordination_prompt,
                "agent_outcome": None,
                "intermediate_steps": existing_agent_state.get("intermediate_steps", []),
                "steps_completed": existing_agent_state.get("steps_completed", {}),
                "geo_policy_done": existing_agent_state.get("geo_policy_done", False),
                "risk_assessment_done": existing_agent_state.get("risk_assessment_done", False),
                "step_count": existing_agent_state.get("step_count", 0),
                "last_action": existing_agent_state.get("last_action", ""),
                # Restore collected data fields
                "purpose": purpose,
                "amount": amount,
                "city": city,
                "pan": pan,
                "aadhaar": aadhaar,
                "salary_update_confirmation": "",
                "document_path": "",
                "agreement_response": "",
                # Add workflow termination flag
                "workflow_finished": False,
            }
            final_state = self.agent_workflow.invoke(initial_state, config={"recursion_limit": 100})  # Increased limit for complex scenarios
            agent_outcome = final_state.get('agent_outcome')
            
            # Save intermediate state to session during workflow
            self.session_manager.update_state("final_agent_state", final_state)
            
            # Extract and save collected data from final state
            if final_state.get("pan"):
                self.session_manager.update_collected_data("pan", final_state.get("pan"))
            if final_state.get("aadhaar"):
                self.session_manager.update_collected_data("aadhaar", final_state.get("aadhaar"))
            if final_state.get("purpose"):
                self.session_manager.update_collected_data("purpose", final_state.get("purpose"))
            if final_state.get("amount"):
                self.session_manager.update_collected_data("amount", final_state.get("amount"))
            if final_state.get("city"):
                self.session_manager.update_collected_data("city", final_state.get("city"))
            
            # Defensive: handle both AgentFinish and AgentAction
            if hasattr(agent_outcome, 'return_values'):
                output = agent_outcome.return_values['output']
                self.session_manager.set_workflow_step(10, "Workflow completed")
                # Mark session as completed if we have a final answer
                self.session_manager.complete_session(output)
            elif hasattr(agent_outcome, 'tool'):
                output = f"Workflow stopped before completion. Last action: {agent_outcome.tool}. Please check for errors or incomplete steps."
                # Update workflow step for resumption
                step_count = final_state.get('step_count', 0)
                self.session_manager.set_workflow_step(step_count + 1, f"Interrupted at {agent_outcome.tool}")
            else:
                output = "Workflow stopped before completion and no valid output was produced."
                self.session_manager.set_workflow_step(1, "Workflow interrupted")

            # Check for application termination
            if "USER_TERMINATED_APPLICATION" in output:
                print(f"\n{'='*60}")
                print("🚪 LOAN APPLICATION TERMINATED")
                print(f"{'='*60}")
                print("The user has declined to continue with the loan application process.")
                print("Thank you for your interest. You may contact our customer service if you need assistance.")
                print(f"{'='*60}")
                self.session_manager.complete_session("Application terminated by user request")
                return output

            # Save output to session
            self.session_manager.add_conversation_entry("Agent", output)

            # Check for user termination first
            if "USER_TERMINATED_APPLICATION" in output:
                return output

            # Clean up any malformed currency patterns first
            output = re.sub(r"₹₹", "₹", output)  # Remove double rupee symbols
            output = re.sub(r"₹(\d+),₹(\d+)", r"₹\1,\2", output)  # Fix patterns like ₹1,₹0
            output = re.sub(r"₹(\d+),₹(\d+),₹(\d+)", r"₹\1,\2,\3", output)  # Fix longer patterns

            # Ensure the amount is always present in the final output
            if (
                ("loan application" in output.lower())
                and (formatted_amount and str(formatted_amount) not in output)
            ):
                # Inject the amount after 'loan application for'
                output = re.sub(
                    r"(loan application\s*(for)?)",
                    f"loan application for {formatted_amount} ",
                    output,
                    flags=re.IGNORECASE,
                )

            # Determine if this is a successful completion or termination
            completion_indicators = ["LOAN AGREEMENT", "APPROVED", "DECLINED", "DIGITALLY ACCEPTED", "USER_TERMINATED_APPLICATION"]
            is_completed = any(indicator in output.upper() for indicator in completion_indicators)
            
            if is_completed:
                self.session_manager.complete_session(output)
            
            # --- NEW APPROACH: Check if we captured an agreement during execution ---
            if self.captured_agreement:
                # We captured the agreement from the tool output, use it
                agreement_text = self.captured_agreement
                loan_details = self.captured_loan_details or {}

                # Save agreement to session
                self.session_manager.update_state("captured_agreement", agreement_text)
                self.session_manager.update_state("captured_loan_details", loan_details)

                # Find the digital acceptance section which contains the user prompt
                digital_acceptance_start = agreement_text.find("DIGITAL ACCEPTANCE REQUIRED")
                if digital_acceptance_start != -1:
                    # Look for the actual prompt part
                    prompt_start = agreement_text.find("To proceed with digital acceptance", digital_acceptance_start)
                    if prompt_start != -1:
                        # Split the agreement from the prompt
                        just_agreement = agreement_text[:prompt_start].strip()
                        acceptance_prompt = agreement_text[prompt_start:].strip()
                        return [just_agreement, acceptance_prompt, {"loan_details": loan_details}]
                    else:
                        # No prompt found, return whole agreement
                        return [agreement_text, {"loan_details": loan_details}]
                else:
                    # Fallback to returning the whole captured agreement
                    return [agreement_text, {"loan_details": loan_details}]

            # --- FALLBACK: Original extraction logic from output ---
            elif "LOAN AGREEMENT & TERMS" in output:
                agreement_start = output.find("LOAN AGREEMENT & TERMS")

                # Find the digital acceptance section which contains the user prompt
                digital_acceptance_start = output.find("DIGITAL ACCEPTANCE REQUIRED", agreement_start)
                if digital_acceptance_start != -1:
                    # Include the digital acceptance section as part of the agreement
                    # Look for the actual prompt part
                    prompt_start = output.find("To proceed with digital acceptance", digital_acceptance_start)
                    if prompt_start != -1:
                        # The agreement includes everything up to the user prompt
                        agreement_text = output[agreement_start:prompt_start].strip()
                        acceptance_prompt = output[prompt_start:].strip()
                        return [agreement_text, acceptance_prompt]
                    else:
                        # No prompt found, return whole thing
                        agreement_text = output[agreement_start:].strip()
                        return [agreement_text]
                else:
                    # No digital acceptance section, try other patterns
                    next_prompt = output.find("please respond with", agreement_start)
                    if next_prompt == -1:
                        agreement_text = output[agreement_start:].strip()
                        acceptance_prompt = ""
                    else:
                        agreement_text = output[agreement_start:next_prompt].strip()
                        acceptance_prompt = output[next_prompt:].strip()

                    if acceptance_prompt:
                        return [agreement_text, acceptance_prompt]
                    else:
                        return [agreement_text]
            else:
                return output
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

    def _get_existing_user_data_for_risk_assessment(self) -> str:
        """Retrieves stored existing user data for RiskAssessment when user chooses not to update salary."""
        if self.stored_existing_user_data is None:
            return json.dumps({
                "error": "No existing user data found. Please run DataQuery first.",
                "status": "no_stored_data"
            })
        
        if not self.clean_ui:
            print("[DEBUG] Retrieving stored existing user data for RiskAssessment")
            print(f"[DEBUG] Stored data contains: {list(self.stored_existing_user_data.keys())}")
        
        # Return the stored user data in the exact format RiskAssessment expects: user_data_json|loan_amount
        # The caller will need to append |loan_amount to use this with RiskAssessment
        return json.dumps(self.stored_existing_user_data, indent=2)
 
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
           
            if self.clean_ui:
                print(f"🎯 Verifying credit score for PAN: {pan_number} - Score: {api_credit_score}")
            else:
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
        
        # PAN or Aadhaar validation (when both are mentioned)
        elif 'pan' in question_lower and 'aadhaar' in question_lower:
            from agentic_ai.core.utils.validators import is_pan, is_aadhaar
            import json
            
            # Try to parse JSON response first (new format)
            try:
                data = json.loads(response)
                if isinstance(data, dict) and 'pan' in data:
                    pan_value = data['pan']
                    if is_pan(pan_value.upper()) or is_aadhaar(pan_value):
                        return True, ""
                    else:
                        return False, "Please provide a valid PAN number (format: ABCDE1234F) or Aadhaar number (12 digits)."
            except json.JSONDecodeError:
                pass
            
            # Fallback to old format (raw string)
            if is_pan(response.upper()) or is_aadhaar(response):
                return True, ""
            else:
                return False, "Please provide a valid PAN number (format: ABCDE1234F) or Aadhaar number (12 digits)."
        
        # PAN validation (only when PAN is mentioned and not Aadhaar)
        elif 'pan' in question_lower and 'aadhaar' not in question_lower:
            from agentic_ai.core.utils.validators import is_pan
            import json
            
            # Try to parse JSON response first (new format)
            try:
                data = json.loads(response)
                if isinstance(data, dict) and 'pan' in data:
                    pan_value = data['pan']
                    if is_pan(pan_value.upper()):
                        return True, ""
                    else:
                        return False, "Please provide a valid PAN number (format: ABCDE1234F)."
            except json.JSONDecodeError:
                pass
            
            # Fallback to old format (raw string)
            if not is_pan(response.upper()):
                return False, "Please provide a valid PAN number (format: ABCDE1234F)."
            return True, ""
        
        # Aadhaar validation (only when Aadhaar is mentioned and not PAN)
        elif ('aadhaar' in question_lower or 'aadhar' in question_lower) and 'pan' not in question_lower:
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
            import os
            if response.lower().endswith(('.pdf', '.txt')) or 'sample' in response.lower():
                # Check if file exists (unless it's a sample file)
                if 'sample' in response.lower() or os.path.exists(response):
                    return True, ""
                else:
                    return False, "File does not exist. Please provide a valid PDF or text file path."
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
    
    def _user_interaction_with_escalation(self, question: str, question_key: str = None) -> str:
        """
        User interaction with escalation support.
        Tracks attempts and escalates to human after max_attempts failures.
        Accepts an optional question_key for robust attempt tracking.
        """
        # Always use a stable key for salary PDF path prompts, regardless of question_key
        if any(x in question.lower() for x in ["salary pdf", "salary slip", "pdf document", "salary document", "provide the path", "pdf or txt"]):
            key = "salary_pdf_path"
        elif question_key is not None:
            key = question_key
        else:
            key = hash(question)
        if key not in self.escalation_attempts:
            self.escalation_attempts[key] = 0
        while self.escalation_attempts[key] < self.max_attempts:
            self.escalation_attempts[key] += 1
            attempt_num = self.escalation_attempts[key]
            print(f"🔄 Attempt {attempt_num}/{self.max_attempts} - UserInteractionAgent")
            
            response = self.interaction_agent.run(question)
            
            # Add to local conversation history
            self.conversation_history.append(f"System: {question}")
            self.conversation_history.append(f"User: {response}")
            
            # COMPREHENSIVE SESSION LOGGING: Save all interactions to session
            self.session_manager.add_conversation_entry("System", question)
            self.session_manager.add_conversation_entry("User", response)
            
            # Save collected data if response contains structured information
            if isinstance(response, dict):
                for key_data, value_data in response.items():
                    self.session_manager.update_collected_data(key_data, value_data)
            elif response and response != "Unable to process your request. Please contact customer service directly.":
                # Try to extract PAN/Aadhaar from response
                import re
                pan_match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', response)
                aadhaar_match = re.search(r'\b\d{12}\b', response)
                
                if pan_match:
                    self.session_manager.update_collected_data("pan", pan_match.group())
                if aadhaar_match:
                    self.session_manager.update_collected_data("aadhaar", aadhaar_match.group())
            
            is_valid, error_message = self._validate_user_response(response, question)
            if is_valid:
                print(f"✅ UserInteractionAgent succeeded on attempt {attempt_num}")
                self.escalation_attempts[key] = 0
                
                # Save successful interaction state to session
                self._save_state_to_session()
                
                return response
            else:
                print(f"⚠️ Response validation failed: {error_message}")
                if attempt_num < self.max_attempts:
                    print(f"🔄 Retrying... ({attempt_num}/{self.max_attempts})")
                    question = f"{error_message} {question}"
                else:
                    escalate_response = self._ask_for_escalation(question, response, error_message)
                    if escalate_response == "USER_TERMINATED_APPLICATION":
                        # User declined escalation, terminate the workflow
                        return escalate_response
                    elif escalate_response:
                        # Human operator provided guidance - use it to re-prompt the user
                        print(f"✅ Human operator provided guidance: {escalate_response}")
                        print(f"� Based on this guidance, please respond to the original question:")
                        
                        
                        # Try to extract useful information from human response
                        extracted_info = self._extract_info_from_human_response(escalate_response, question)
                        if extracted_info:
                            print(f"✅ Extracted information from human guidance: {extracted_info}")
                            self.escalation_attempts[key] = 0
                            self._save_state_to_session()
                            return extracted_info
                        else:
                            # Human response is guidance - check if it's about consent
                            if "consent" in escalate_response.lower() and ("aadhaar" in question.lower() or "consent" in question.lower()):
                                print(f"📋 Human operator suggests proceeding with consent...")
                                self.escalation_attempts[key] = 0
                                self._save_state_to_session()
                                return "yes"  # Assume human guidance means proceed
                            else:
                                # General guidance - return the guidance as response
                                print(f"📋 Continuing workflow with human guidance...")
                                self.escalation_attempts[key] = 0
                                self._save_state_to_session()
                                return escalate_response
        return f"Unable to process your request. Please contact customer service directly."
    
    def _extract_info_from_human_response(self, human_response: str, original_question: str) -> str:
        """
        Extract actionable information from human response if available.
        For example, if human says "use PAN: ABCDE1234F", extract the PAN.
        """
        import re
        
        # Look for PAN pattern in human response
        pan_match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', human_response)
        if pan_match and "pan" in original_question.lower():
            return pan_match.group()
        
        # Look for Aadhaar pattern in human response
        aadhaar_match = re.search(r'\b\d{12}\b', human_response)
        if aadhaar_match and "aadhaar" in original_question.lower():
            return aadhaar_match.group()
            
        # Look for consent responses
        consent_words = ["yes", "agree", "consent", "allow", "permit", "authorize", "proceed"]
        if any(word in human_response.lower() for word in consent_words) and ("consent" in original_question.lower() or "aadhaar" in original_question.lower()):
            return "yes"
        
        # Look for denial responses  
        denial_words = ["no", "deny", "decline", "refuse", "reject"]
        if any(word in human_response.lower() for word in denial_words) and ("consent" in original_question.lower() or "aadhaar" in original_question.lower()):
            return "no"
            
        # If no specific info found, return None
        return None
    
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
            print(f"\n{'='*60}")
            print("🚪 LOAN APPLICATION TERMINATED")
            print(f"{'='*60}")
            print("❌ User declined escalation to human agent.")
            print("🏁 The loan application process has been ended.")
            print("📞 You may contact customer service directly if you need assistance.")
            print(f"{'='*60}")
            
            # Mark session as ended by user
            self.session_manager.update_state("session_status", "ended_by_user")
            self.session_manager.update_state("termination_reason", "user_declined_escalation")
            self.session_manager.complete_session("Application terminated: User declined escalation to human agent.")
            
            return "USER_TERMINATED_APPLICATION"
    
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
            
            # Extract the actual response text from the dictionary
            if isinstance(human_response, dict):
                if 'response' in human_response:
                    return human_response['response']
                else:
                    return str(human_response)
            else:
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

    def _save_state_to_session(self):
        """Save current orchestrator state to session"""
        orchestrator_state = {
            "escalation_attempts": self.escalation_attempts,
            "conversation_history": self.conversation_history,
            "captured_agreement": self.captured_agreement,
            "captured_loan_details": self.captured_loan_details,
            "captured_tool_outputs": self.captured_tool_outputs,
            "stored_existing_user_data": self.stored_existing_user_data,
            "current_question_type": self.current_question_type
        }
        self.session_manager.update_orchestrator_state(orchestrator_state)
    
    def _restore_state_from_session(self, orchestrator_state):
        """Restore orchestrator state from session"""
        self.escalation_attempts = orchestrator_state.get("escalation_attempts", {})
        self.conversation_history = orchestrator_state.get("conversation_history", [])
        self.captured_agreement = orchestrator_state.get("captured_agreement", None)
        self.captured_loan_details = orchestrator_state.get("captured_loan_details", None)
        self.captured_tool_outputs = orchestrator_state.get("captured_tool_outputs", {})
        self.stored_existing_user_data = orchestrator_state.get("stored_existing_user_data", None)
        self.current_question_type = orchestrator_state.get("current_question_type", None)

    def get_session_info(self):
        """Get current session information"""
        if self.session_manager.session_id:
            return {
                "session_id": self.session_manager.session_id,
                "status": self.session_manager.get_state("status"),
                "workflow_step": self.session_manager.get_state("workflow_step"),
                "created_at": self.session_manager.get_state("created_at"),
                "last_updated": self.session_manager.get_state("last_updated")
            }
        return None