# cli.py
from agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator import LoanAgentOrchestrator
from agentic_ai.core.llm.factory import LLMFactory
from agentic_ai.modules.loan_processing.agents.base_agent import BaseAgent

def process_loan_application(user_request: str):
    """
    Processes a single loan query.
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
    
    orchestrator = LoanAgentOrchestrator()
    
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
