import os
import json
import re
from typing import Dict, Any, Optional
import warnings
from groq import Groq
import pandas as pd

# Import the provided classes
from Fraud import Fraud_AML_Agent
from Loan import Loan_processing_AI_agent2
from Banking import BankingServicesAgent

# Suppress warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ConversationManager:
    """Manages conversation history and state"""
    
    def __init__(self):
        self.active_agent = None
        self.user_id = None
        self.conversation_state = "active"  # IDENTIFIER: active, account_creation, banking_session, loan_request, fraud_investigation
        self.collected_data = {}
        self.last_intent = None
        self.conversation_history = []
    
    def reset(self):
        """Reset conversation history"""
        self.active_agent = None
        self.user_id = None
        self.conversation_state = "active"
        self.collected_data = {}
        self.last_intent = None
        # Maintain a limited history
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-5:]
    
    def add_interaction(self, user_input: str, agent_response: str, intent: str):
        """Add an interaction to the history"""
        self.conversation_history.append({
            "user_input": user_input,
            "agent_response": agent_response,
            "intent": intent,
            "timestamp": str(pd.Timestamp.now())
        })
        self.last_intent = intent
    
    def is_continuing(self, user_input: str, current_intent: str) -> bool:
        """Determine if the input continues the current conversation"""
        user_input_lower = user_input.lower()
        
        # Strong intent indicators
        loan_indicators = ['loan', 'credit', 'apply', 'emi', 'borrow']
        fraud_indicators = ['fraud', 'suspicious', 'aml', 'investigate']
        banking_indicators = ['account', 'balance', 'transfer', 'card', 'kyc']
        
        # If active, no continuation
        if self.conversation_state == "active":
            return False
        
        # If in account_creation, continue unless explicit new intent
        if self.conversation_state == "account_creation":
            new_request_keywords = loan_indicators + fraud_indicators
            is_new_request = any(keyword in user_input_lower for keyword in new_request_keywords)
            return not is_new_request
        
        # If in banking_session, continue only if banking-related and no loan/fraud indicators
        if self.conversation_state == "banking_session":
            has_loan = any(keyword in user_input_lower for keyword in loan_indicators)
            has_fraud = any(keyword in user_input_lower for keyword in fraud_indicators)
            has_banking = any(keyword in user_input_lower for keyword in banking_indicators)
            return current_intent == "banking_services" and has_banking and not (has_loan or has_fraud)
        
        # If in loan_request, continue only if loan-related
        if self.conversation_state == "loan_request":
            has_banking = any(keyword in user_input_lower for keyword in banking_indicators)
            has_fraud = any(keyword in user_input_lower for keyword in fraud_indicators)
            return current_intent == "loan_processing" and not (has_banking or has_fraud)
        
        # If in fraud_investigation, continue only if fraud-related
        if self.conversation_state == "fraud_investigation":
            has_banking = any(keyword in user_input_lower for keyword in banking_indicators)
            has_loan = any(keyword in user_input_lower for keyword in loan_indicators)
            return current_intent == "fraud_analysis" and not (has_banking or has_loan)
        
        return False

class OrchestrationAgent:
    def __init__(self):
        # Initialize Groq client
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("⚠️ Warning: GROQ_API_KEY environment variable not set.")
            print("Some features may be limited. Please set your API key for full functionality.")
            self.groq_client = None
        else:
            try:
                self.groq_client = Groq(api_key=self.api_key)
                print("✅ Groq client initialized successfully")
            except Exception as e:
                print(f"⚠️ Failed to initialize Groq client: {e}")
                self.groq_client = None

        # Initialize conversation context
        self.context = ConversationManager()

        # Initialize the sub-agents with error handling
        self.fraud_agent = None
        self.loan_agent = None
        self.banking_agent = None
        
        # Initialize Banking Agent
        try:
            self.banking_agent = BankingServicesAgent()
            print("✅ Banking Services Agent initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Banking Agent: {e}")
            print("Banking services will not be available.")
            
        # Initialize Fraud Agent
        try:
            self.fraud_agent = Fraud_AML_Agent()
            print("✅ Fraud Detection Agent initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Fraud Agent: {e}")
            print("Fraud detection services will not be available.")
            
        # Initialize Loan Agent
        try:
            self.loan_agent = Loan_processing_AI_agent2
            status = self.loan_agent.get_agent_status()
            print(f"✅ Loan Processing Agent initialized successfully. Status: {status}")
        except Exception as e:
            print(f"❌ Failed to initialize Loan Agent: {e}")
            print("Loan processing services will not be available.")
            self.loan_agent = None

    def classify_intent(self, user_input: str) -> Dict[str, Any]:
        """Classify the user's intent using an LLM to determine which agent to route to."""
        
        # If no Groq client, use fallback classification
        if not self.groq_client:
            return self._fallback_intent_classification(user_input)
            
        prompt = f"""
You are an intent classification system for routing user queries to specialized agents.
The user input is: "{user_input}"

Your task:
1. Analyze the input to determine the intent, which can be one of:
   - "fraud_analysis": Queries about fraud detection, AML compliance, transaction analysis, or risk (e.g., "investigate fraud for user 123", "suspicious transaction").
   - "loan_processing": Queries about loans, credit assessment, or financial products (e.g., "apply for a ₹5 lakh loan", "check loan status with PAN ABCDE1234F").
   - "banking_services": Queries about accounts, balances, transfers, cards, KYC, or general banking (e.g., "check balance for U1001", "open new account").
   - "unclear": Queries that do not clearly fit any category.

2. Extract identifiers:
   - For fraud_analysis: Numeric User ID (e.g., "user 123", "ID 456").
   - For loan_processing: PAN (e.g., "ABCDE1234F") or Aadhaar (12 digits).
   - For banking_services: User ID (e.g., "U1001", "user U1002") or "NEWUSER" for account opening.

3. Return JSON:
   ```json
   {{
       "intent": "fraud_analysis|loan_processing|banking_services|unclear",
       "user_id": "extracted_user_id|null",
       "identifier": "PAN_or_Aadhaar|email|phone|null"
   }}
   ```

Instructions:
- Prioritize loan_processing for inputs mentioning "loan", "credit", "EMI", or "apply" unless banking terms like "account" or "transfer" are present.
- Classify as banking_services for account-related terms like "balance", "transfer", "card", or "KYC".
- Default to unclear only if no specific intent is identifiable.
- Examples:
  - "check loan status for PAN ABCDE1234F" → {{"intent": "loan_processing", "user_id": null, "identifier": "ABCDE1234F"}}
  - "transfer ₹1000 to U1002" → {{"intent": "banking_services", "user_id": "U1002", "identifier": null}}
  - "is my transaction safe for user 456" → {{"intent": "fraud_analysis", "user_id": "456", "identifier": null}}
  - "open an account" → {{"intent": "banking_services", "user_id": "NEWUSER", "identifier": null}}
  - "abc@def.com" → {{"intent": "banking_services", "user_id": null, "identifier": "abc@def.com"}}
  - "PZTPS4304Y" → {{"intent": "banking_services", "user_id": null, "identifier": "PZTPS4304Y"}}

Provide only the JSON output.
"""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                max_tokens=200,
                temperature=0.7
            )
            result = response.choices[0].message.content
            print(f"[DEBUG] Intent Classification (LLM): {result}")
            return json.loads(result)
        except Exception as e:
            print(f"❌ LLM intent classification failed: {str(e)}")
            return self._fallback_intent_classification(user_input)
    
    def _fallback_intent_classification(self, user_input: str) -> Dict[str, Any]:
        """Fallback intent classification using keyword matching."""
        user_input_lower = user_input.lower()
        
        # Check data responses
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', user_input.strip()):
            return {"intent": "banking_services", "user_id": None, "identifier": user_input.strip()}
        if re.match(r'^[A-Z]{5}\d{4}[A-Z]$', user_input.strip().upper()):
            return {"intent": "banking_services", "user_id": None, "identifier": user_input.strip().upper()}
        if re.match(r'^\d{12}$', user_input.strip()):
            return {"intent": "banking_services", "user_id": None, "identifier": user_input.strip()}
        if re.match(r'^\d{10}$', user_input.strip()):
            return {"intent": "banking_services", "user_id": None, "identifier": user_input.strip()}
        
        # Define keywords with weights
        banking_keywords = {'account': 2, 'balance': 2, 'transfer': 2, 'card': 2, 'kyc': 2, 'bank': 1, 'open': 2, 'deposit': 1, 'withdraw': 1}
        fraud_keywords = {'fraud': 3, 'transaction': 1, 'risk': 2, 'suspicious': 3, 'aml': 3, 'compliance': 2, 'investigate': 2}
        loan_keywords = {'loan': 3, 'credit': 2, 'apply': 2, 'emi': 3, 'borrow': 2, 'lakh': 1, 'interest': 2}
        
        # Calculate scores
        banking_score = sum(weight for keyword, weight in banking_keywords.items() if keyword in user_input_lower)
        fraud_score = sum(weight for keyword, weight in fraud_keywords.items() if keyword in user_input_lower)
        loan_score = sum(weight for keyword, weight in loan_keywords.items() if keyword in user_input_lower)
        
        # Negative keywords to refine intent
        if 'balance' in user_input_lower or 'transfer' in user_input_lower:
            loan_score = 0  # Exclude loan_processing
        if 'loan' in user_input_lower:
            banking_score = max(0, banking_score - 2)  # Reduce banking score
        
        # Determine intent
        if banking_score > fraud_score and banking_score > loan_score:
            intent = "banking_services"
        elif fraud_score > loan_score:
            intent = "fraud_analysis"
        elif loan_score > 0:
            intent = "loan_processing"
        else:
            intent = "unclear"
        
        # Extract User ID
        user_id = None
        u_format_match = re.search(r'\b[uU](\d{4})\b', user_input)
        if u_format_match:
            user_id = f"U{u_format_match.group(1)}"
        else:
            user_u_match = re.search(r'\b(?:user\s*id?\s*|id\s*)[uU](\d{4})\b', user_input, re.IGNORECASE)
            if user_u_match:
                user_id = f"U{user_u_match.group(1)}"
            else:
                user_num_match = re.search(r'\b(?:user\s*id?\s*|id\s*|user\s*)(\d+)\b', user_input_lower)
                if user_num_match:
                    user_id = user_num_match.group(1)
        
        # Handle new account requests
        new_account_keywords = ['open', 'new', 'create', 'register', 'signup', 'start']
        if any(keyword in user_input_lower for keyword in new_account_keywords):
            intent = "banking_services"
            user_id = "NEWUSER"
        
        # Extract identifier
        pan_match = re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', user_input.upper())
        aadhaar_match = re.search(r'\b\d{12}\b', user_input)
        identifier = pan_match.group(0) if pan_match else (aadhaar_match.group(0) if aadhaar_match else None)
        
        print(f"[DEBUG] Intent Classification (Fallback): {{'intent': '{intent}', 'user_id': {user_id}, 'identifier': {identifier}}}")
        return {
            "intent": intent,
            "user_id": user_id,
            "identifier": identifier
        }

    def process_conversation_turn(self, user_input: str) -> str:
        """Process a single conversation turn with context awareness"""
        
        if not user_input.strip():
            return "🤔 Please enter a request."
        
        if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
            self.context.reset()
            return "🔄 Returning to the main orchestration agent. Please enter your next request."
        
        # Classify intent
        intent_analysis = self.classify_intent(user_input)
        print(f"🔎 Intent Analysis: {intent_analysis}")
        
        current_intent = intent_analysis["intent"]
        
        # Check if this is a continuation of current conversation
        if self.context.is_continuing(user_input, current_intent):
            print(f"🔄 Continuing {self.context.conversation_state} conversation...")
            
            # Continue with the active agent
            if self.context.active_agent == "banking" and self.banking_agent:
                response = self.banking_agent.process_single_query(user_input, self.context.user_id or "NEWUSER")
                
                # Check if account was created (extract new user ID)
                if "Account created successfully" in response:
                    user_id_match = re.search(r'User ID: (U\d+)', response)
                    if user_id_match:
                        self.context.user_id = user_id_match.group(1)
                        self.context.conversation_state = "banking_session"
                        print(f"🎉 Account created! New User ID: {self.context.user_id}")
                
                self.context.add_interaction(user_input, response, "banking_services")
                return response
            
            elif self.context.active_agent == "loan" and self.loan_agent:
                response = self.loan_agent.process_single_query(user_input)
                self.context.add_interaction(user_input, response, "loan_processing")
                
                # Check if more input is needed
                if "🤔" in response or "Your response" in response:
                    print("[DEBUG] Awaiting additional user input...")
                    user_response = input("Your response: ").strip()
                    if user_response:
                        return self.process_conversation_turn(user_response)
                
                return response
            
            elif self.context.active_agent == "fraud" and self.fraud_agent:
                response = self.fraud_agent.process_single_query(user_input)
                self.context.add_interaction(user_input, response, "fraud_analysis")
                return response
        
        # New conversation or change of context
        if current_intent != self.context.last_intent:
            print(f"🔄 Switching context from {self.context.last_intent} to {current_intent}")
        
        # Route to appropriate agent
        if current_intent == "unclear":
            return self._handle_unclear_intent()
        
        elif current_intent == "fraud_analysis":
            return self._handle_fraud_analysis(user_input, intent_analysis)
        
        elif current_intent == "loan_processing":
            return self._handle_loan_processing(user_input, intent_analysis)
        
        elif current_intent == "banking_services":
            return self._handle_banking_services(user_input, intent_analysis)
        
        else:
            return "I'm not sure how to help with that request."
    
    def _handle_unclear_intent(self) -> str:
        """Handle unclear intent"""
        return """🤔 I'm not sure which service you need. Please clarify:
  - For fraud detection: 'investigate fraud for user 123'
  - For loan processing: 'apply for a ₹5 lakh loan with PAN ABCDE1234F'
  - For banking services: 'check my balance' or 'open new account'"""
    
    def _handle_fraud_analysis(self, user_input: str, intent_analysis: Dict) -> str:
        """Handle fraud analysis requests"""
        if not self.fraud_agent:
            return "❌ Fraud Detection Agent is not available."
        
        print("\n🔍 Handing off to Fraud Detection Agent...")
        self.context.active_agent = "fraud"
        self.context.conversation_state = "fraud_investigation"
        self.context.user_id = intent_analysis.get("user_id")
        
        response = self.fraud_agent.process_single_query(user_input)
        self.context.add_interaction(user_input, response, "fraud_analysis")
        return response
    
    def _handle_loan_processing(self, user_input: str, intent_analysis: Dict) -> str:
        """Handle loan processing requests"""
        if not self.loan_agent:
            return "❌ Loan Processing Agent is not available."
        
        print("\n🏦 Handing off to Loan Processing Agent...")
        self.context.active_agent = "loan"
        self.context.conversation_state = "loan_request"
        
        response = self.loan_agent.process_single_query(user_input)
        self.context.add_interaction(user_input, response, "loan_processing")
        
        # Check if more input is needed
        if "🤔" in response or "Your response" in response:
            print("[DEBUG] Awaiting additional user input...")
            user_response = input("Your response: ").strip()
            if user_response:
                return self.process_conversation_turn(user_response)
        
        return response
    
    def _handle_banking_services(self, user_input: str, intent_analysis: Dict) -> str:
        """Handle banking services requests"""
        if not self.banking_agent:
            return "❌ Banking Services Agent is not available."
        
        print("\n🏪 Handing off to Banking Services Agent...")
        
        # Enhanced User ID handling for banking services
        user_id = intent_analysis.get("user_id")
        
        # Keywords that definitely indicate new account creation
        new_account_keywords = ['open', 'new', 'create', 'register', 'signup', 'start', 'begin']
        is_new_account = any(keyword in user_input.lower() for keyword in new_account_keywords)
        
        # Keywords that definitely need existing user ID
        existing_user_keywords = ['balance', 'transfer', 'send', 'statement', 'mini', 'card', 'activate', 'deactivate', 'my account', 'my balance', 'my card']
        needs_existing_user = any(keyword in user_input.lower() for keyword in existing_user_keywords)
        
        # Set conversation state and user_id
        if is_new_account or self.context.conversation_state == "account_creation":
            self.context.conversation_state = "account_creation"
            self.context.active_agent = "banking"
            user_id = "NEWUSER"
            print("🆕 Account creation conversation")
        elif self.context.conversation_state == "banking_session":
            # Continue with existing session
            user_id = self.context.user_id or user_id
            print(f"🔄 Continuing banking session with User ID: {user_id}")
        elif user_id:
            # User ID was extracted from the input
            self.context.user_id = user_id
            self.context.conversation_state = "banking_session"
            self.context.active_agent = "banking"
            print(f"👤 Banking session started with User ID: {user_id}")
        elif needs_existing_user:
            # Operation needs existing user but no ID provided - ask for it
            print("🔍 This operation requires your User ID")
            user_response = input("Please provide your User ID (e.g., U1001): ").strip()
            if not user_response:
                return "❌ User ID is required for this operation."
            self.context.user_id = user_response
            self.context.conversation_state = "banking_session"
            self.context.active_agent = "banking"
            print(f"👤 Banking session started with User ID: {user_response}")
            return self._handle_banking_services(user_response, intent_analysis)
        else:
            # General banking query or data response
            self.context.conversation_state = "banking_session"
            self.context.active_agent = "banking"
            user_id = self.context.user_id or "NEWUSER"
            print(f"💡 General banking query with User ID: {user_id}")
        
        response = self.banking_agent.process_single_query(user_input, user_id)
        
        # Check if account was created (extract new user ID)
        if "Account created successfully" in response:
            user_id_match = re.search(r'User ID: (U\d+)', response)
            if user_id_match:
                self.context.user_id = user_id_match.group(1)
                self.context.conversation_state = "banking_session"
                print(f"🎉 Account created! New User ID: {self.context.user_id}")
        
        self.context.add_interaction(user_input, response, "banking_services")
        return response

    def run(self):
        """Run the orchestration agent to classify intent and hand off to the appropriate sub-agent."""
        print("=" * 80)
        print("🤖 ORCHESTRATION AGENT - COMPLETE BANKING SYSTEM")
        print("=" * 80)
        print("📅 System Date: June 04, 2025, 07:39 PM IST")
        print("\n💬 I can help you with:")
        print("• 🛡️ Fraud detection, AML compliance, and transaction analysis")
        print("• 🏦 Loan applications, credit assessment, and policy validation")
        print("• 🏪 Banking services: account creation, balance inquiry, transfers, card management")
        print("\n🗣️ Examples:")
        print("  - 'Investigate fraud for user 123'")
        print("  - 'Apply for a ₹5 lakh loan with PAN ABCDE1234F in Mumbai'")
        print("  - 'Check my account balance for user U1001'")
        print("  - 'Open a new bank account'")
        print("  - 'Transfer ₹1000 to account 1002001000'")
        print("  - 'Activate my card'")
        print("\nType 'exit' to return to the main menu or 'quit' to stop.")
        print("=" * 80)

        while True:
            try:
                user_input = input("\nYour request: ").strip()
                response = self.process_conversation_turn(user_input)
                print(f"\n🤖 Response:\n{response}")

            except KeyboardInterrupt:
                print("\n\n👋 Thanks for using the Orchestration Agent! Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}. Please try again.")

    def get_system_status(self) -> Dict[str, Any]:
        """Get the status of all agents in the system."""
        status = {
            "orchestrator": {
                "status": "operational",
                "groq_api_available": bool(self.api_key),
                "conversation_state": self.context.conversation_state,
                "active_agent": self.context.active_agent,
                "user_id": self.context.user_id
            }
        }
        
        if self.fraud_agent:
            try:
                status["fraud_agent"] = self.fraud_agent.get_agent_status()
            except:
                status["fraud_agent"] = {"status": "error"}
        else:
            status["fraud_agent"] = {"status": "not_initialized"}
            
        if self.loan_agent:
            try:
                status["loan_agent"] = self.loan_agent.get_agent_status()
            except:
                status["loan_agent"] = {"status": "error"}
        else:
            status["loan_agent"] = {"status": "not_initialized"}
            
        if self.banking_agent:
            try:
                status["banking_agent"] = self.banking_agent.get_agent_status()
            except:
                status["banking_agent"] = {"status": "error"}
        else:
            status["banking_agent"] = {"status": "not_initialized"}
            
        return status

    def process_single_request(self, user_input: str) -> str:
        """
        Process a single request and return response.
        Useful for API integration or programmatic access.
        """
        return self.process_conversation_turn(user_input)

if __name__ == "__main__":
    try:
        orchestrator = OrchestrationAgent()
        orchestrator.run()
    except Exception as e:
        print(f"❌ Failed to start Orchestration Agent: {e}")
        print("Please ensure all dependencies are installed and API keys are set.")