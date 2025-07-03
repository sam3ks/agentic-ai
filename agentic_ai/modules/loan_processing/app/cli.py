# cli.py
from agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator import LoanAgentOrchestrator
from agentic_ai.core.llm.factory import LLMFactory
from agentic_ai.modules.loan_processing.agents.base_agent import BaseAgent
from agentic_ai.modules.loan_processing.agents.agreement_agent import AgreementAgent

def process_loan_application(user_request: str, automate_user: bool = False, customer_profile=None):
    """
    Processes a single loan query. If automate_user is True, uses CustomerAgent to automate user input.
    """
    print("=" * 60)
    print("🏦 MULTI-AGENT LOAN PROCESSING SYSTEM")
    print("=" * 60)

    if not user_request:
        print("❌ Request cannot be empty")
        return
    
    # Initialize the LLM once at the beginning to prevent multiple initializations
    llm = LLMFactory.get_llm()
    print("✓ LLM initialized successfully")
    
    orchestrator = LoanAgentOrchestrator(automate_user=automate_user, customer_profile=customer_profile)
    
    print(f"\n{'='*60}")
    print("🔄 MULTI-AGENT PROCESSING...")
    print("=" * 60)
    
    result = orchestrator.process_application(user_request)
    
    
    print(f"\n{'='*60}")
    print("✅ PROCESSING COMPLETE")
    print("=" * 60)
    print(result)
    
    # Check if result contains an agreement presentation
    if "LOAN AGREEMENT & TERMS" in result and "DIGITAL ACCEPTANCE REQUIRED" in result and not automate_user:
        print("\n" + "="*60)
        print("📝 AGREEMENT RESPONSE REQUIRED")
        print("="*60)
        
        # Get user response for agreement
        while True:
            try:
                user_response = input("Your response (I AGREE/I ACCEPT to accept, I DECLINE/I REJECT to decline): ").strip()
                
                if not user_response:
                    print("Please provide a response.")
                    continue
                    
                # Process the agreement response
                agreement_agent = AgreementAgent()
                final_result = agreement_agent.capture_digital_acceptance(user_response)
                
                print(f"\n{'='*60}")
                print("📋 AGREEMENT PROCESSED")
                print("="*60)
                print(final_result)
                break
                
            except KeyboardInterrupt:
                print("\nAgreement process cancelled.")
                break
            except Exception as e:
                print(f"Error processing response: {e}")
                print("Please try again.")
