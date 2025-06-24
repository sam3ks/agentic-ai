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
from agentic_ai.core.orchestrator.agent_executor_factory import create_agent_executor
from agentic_ai.core.utils.parsing import parse_initial_user_request
from agentic_ai.core.utils.formatting import format_indian_commas

class LoanAgentOrchestrator:
    """Orchestrates the loan processing workflow."""

    def __init__(self):
        self.data_service = LoanDataService()
        self.data_agent = DataQueryAgent(self.data_service)
        self.geo_agent = GeoPolicyAgent()
        self.risk_agent = RiskAssessmentAgent()
        self.interaction_agent = UserInteractionAgent() # Instantiated here
        self.salary_generator = SalarySheetGeneratorAgent()
        self.salary_retriever = SalarySheetRetrieverAgent()
        self.pdf_extractor = PDFSalaryExtractorAgent()
        self.purpose_agent = LoanPurposeAssessmentAgent() # Add purpose assessment agent
        
        self.tools = self._setup_tools()
        self.agent_executor = create_agent_executor(self.tools)

    def _setup_tools(self):
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
                description="ONLY after GeoPolicyCheck is completed. Perform risk assessment. REQUIRED FORMAT: 'user_data_json|loan_amount' - The user_data_json must be the COMPLETE user data object from either: 1) DataQuery for existing users who don't want to update salary, 2) PDFSalaryExtractor's output if extraction was successful (use the 'user_data' field from the result), or 3) SalarySheetGenerator only if PDF extraction failed. NEVER skip PDF extraction results if successful.",
                func=self.risk_agent.run
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
            )
        ]

    def process_application(self, user_input: str) -> str:
        """Processes a loan application."""
        initial_loan_details = parse_initial_user_request(user_input)
        # Format amount in Indian style for prompt and replace in user_input
        if 'amount' in initial_loan_details and initial_loan_details['amount']:
            formatted_amount = format_indian_commas(initial_loan_details['amount'])
            # Replace all international formatted numbers in user_input with Indian format
            import re
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

        if initial_loan_details.get("purpose", "unknown") == "unknown":
            prompt_parts.append("1. Ask for loan purpose using UserInteraction.")
        prompt_parts.append("2. ALWAYS submit the purpose to LoanPurposeAssessment to evaluate eligibility.")
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
        prompt_parts.append("9. Run RiskAssessment with user data and amount.")
        prompt_parts.append("10. Make a final decision combining LoanPurposeAssessment, GeoPolicyCheck, and RiskAssessment.")
        prompt_parts.append("\nDO NOT SKIP ANY STEP OR CHANGE THE ORDER.")

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
        import re
        def replace_with_indian_commas(match):
            num = int(match.group(0).replace(",", ""))
            return format_indian_commas(num)
        text = re.sub(r"\d{1,3}(?:,\d{3})+|\d{7,}", replace_with_indian_commas, text)
        return text

