# cli.py
from agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator import LoanAgentOrchestrator
from agentic_ai.core.llm.factory import LLMFactory
from agentic_ai.modules.loan_processing.agents.base_agent import BaseAgent

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
    
    # Post-process output for Indian comma formatting
    if hasattr(orchestrator, 'postprocess_output'):
        result = orchestrator.postprocess_output(result)
    elif hasattr(BaseAgent, 'postprocess_output'):
        result = BaseAgent().postprocess_output(result)
    
    print(f"\n{'='*60}")
    print("✅ PROCESSING COMPLETE")
    print("=" * 60)
    print(result)
