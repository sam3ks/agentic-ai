import click
import logging
from agentic_ai.modules.loan_processing.app.cli import process_loan_application
from agentic_ai.core.session.session_manager import SessionManager
import random
import os

# Configure logging for clean CLI output
def setup_clean_logging(verbose=False):
    """Configure logging to reduce verbosity for CLI users"""
    if verbose:
        # Show all logs in verbose mode
        logging.getLogger().setLevel(logging.DEBUG)
        return
    
    # Clean mode: suppress debug logs
    logging.getLogger().setLevel(logging.WARNING)
    
    # Suppress specific noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("agentic_ai.core.orchestrator.agent_executor_factory").setLevel(logging.ERROR)
    
    # Suppress debug logs from our own modules
    logging.getLogger("agentic_ai.modules.loan_processing.agents").setLevel(logging.WARNING)
    logging.getLogger("agentic_ai.core").setLevel(logging.WARNING)
    
    # Keep important user-facing logs only
    logging.getLogger("agentic_ai.modules.loan_processing").setLevel(logging.INFO)

def generate_random_profile():
    purposes = ["home renovation", "education", "wedding", "business expansion", "medical"]
    cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
    amounts = ["100000", "250000", "500000", "750000", "1000000"]
    pan_numbers = ["ABCDE1234F", "FGHIJ5678K", "KLMNO9012P", "AASIL9982X", "OHWQG0796D", "JPYVM1461B"]
    aadhaar_numbers = ["123456789012", "234567890123", "345678901234", "503153508818", "347676851687", "776849406520"]
    return {
        "purpose": random.choice(purposes),
        "amount": random.choice(amounts),
        "city": random.choice(cities),
        "identifier": random.choice(pan_numbers + aadhaar_numbers)
    }

def generate_automated_request(profile):
    return f"I want a loan for {profile['purpose']} of amount {profile['amount']} in {profile['city']}."

@click.command()
@click.argument('session_id', required=False)
@click.option('--customer-agent', is_flag=True, help='Run in automated customer agent mode')
@click.option('--status', help='Check status of a specific session', type=str, default=None)
@click.option('--list', 'list_sessions', is_flag=True, help='List all sessions with their status')
@click.option('--verbose', is_flag=True, help='Show detailed debug output')
def main(session_id, customer_agent, status, list_sessions, verbose):
    """Loan Processing CLI with Session Management"""
    setup_clean_logging(verbose)
    
    # Handle list sessions
    if list_sessions:
        session_manager = SessionManager()
        sessions = session_manager.list_sessions()
        if not sessions:
            print("📋 No sessions found")
        else:
            print("📋 All Sessions:")
            print("=" * 80)
            for session in sessions:
                session_id = session.get("session_id", "unknown")
                status = session.get("status", "unknown")
                created_at = session.get("created_at", "unknown")
                request = session.get("user_request", "No request")[:50] + "..." if len(session.get("user_request", "")) > 50 else session.get("user_request", "No request")
                
                status_icon = "✅" if status == "completed" else "🔄" if status == "active" else "🚪" if status == "ended_by_user" else "❓"
                print(f"{status_icon} {session_id}")
                print(f"   Status: {status.upper()}")
                print(f"   Created: {created_at}")
                print(f"   Request: {request}")
                print()
        return

    # Handle status check
    if status:
        session_manager = SessionManager()
        session_status = session_manager.get_session_status(status)
        if session_status == "not_found":
            print(f"❌ Session {status} not found")
        elif session_status == "completed":
            print(f"✅ Session {status} is COMPLETED")
            print(f"📋 This session was finished successfully. Cannot be resumed.")
        elif session_status == "ended_by_user":
            print(f"🚪 Session {status} was ENDED BY USER")
            print(f"📋 User declined escalation and ended the loan application. Cannot be resumed.")
        elif session_status == "active":
            print(f"🔄 Session {status} is ACTIVE")
            print(f"📋 This session can be resumed with: python run_loan_cli.py {status}")
        else:
            print(f"❓ Session {status} has unknown status: {session_status}")
        return

    # Handle resume session via positional session_id
    if session_id:
        session_manager = SessionManager()
        try:
            # Validate session file exists
            session_file = os.path.join('session_data', f'{session_id}.json')
            if not os.path.exists(session_file):
                print(f"❌ Session {session_id} not found in session_data directory.")
                return
            if session_manager.resume_session(session_id):
                session_status = session_manager.get_session_status(session_id)
                if session_status == "completed":
                    print(f"✅ Session {session_id} is COMPLETED\n📋 This session was finished successfully. Cannot be resumed.")
                    return
                elif session_status == "ended_by_user":
                    print(f"🚪 Session {session_id} was ENDED BY USER\n📋 User declined escalation and ended the loan application. Cannot be resumed.")
                    return
                print(f"✅ Resumed session {session_id}")
                original_request = session_manager.get_state('user_request')
                if original_request:
                    print(f"📋 Original request: {original_request}")
                    collected_data = session_manager.get_state('collected_data', {})
                    process_loan_application(original_request, automate_user=customer_agent, 
                                           customer_profile=collected_data, 
                                           session_id=session_id, clean_ui=not verbose)
                else:
                    print(f"❌ Could not find original request in session {session_id}")
            else:
                session_status = session_manager.get_session_status(session_id)
                if session_status == "completed":
                    print(f"✅ Session {session_id} is COMPLETED\n📋 This session was finished successfully. Cannot be resumed.")
                elif session_status == "ended_by_user":
                    print(f"🚪 Session {session_id} was ENDED BY USER\n📋 User declined escalation and ended the loan application. Cannot be resumed.")
                else:
                    print(f"❌ Could not resume session {session_id}")
        except KeyboardInterrupt:
            print('\n⚠️ Exiting... Saving session. Goodbye')
        return

    if customer_agent:
        # Automated mode: Process one loan application and exit
        try:
            profile = generate_random_profile()
            request = generate_automated_request(profile)
            print(f"[CustomerAgent] Generated loan request: {request}")
            process_loan_application(request, automate_user=customer_agent, customer_profile=profile, clean_ui=not verbose)
            print("✅ CustomerAgent workflow completed. Exiting...")
        except KeyboardInterrupt:
            print('\n⚠️ Exiting... Saving session. Goodbye')
    else:
        # Manual mode: Continue until user chooses to exit
        try:
            while True:
                request = click.prompt('Enter your loan request')
                if request.strip().lower() in ['stop', 'exit', 'quit']:
                    print('Exiting loan processing. Goodbye!')
                    break
                process_loan_application(request, automate_user=customer_agent, customer_profile=None, clean_ui=not verbose)
        except KeyboardInterrupt:
            print('\n⚠️ Exiting... Saving session. Goodbye')

if __name__ == "__main__":
    main()
