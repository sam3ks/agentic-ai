"""
Enhanced Loan Orchestrator with built-in escalation management.

This orchestrator tracks user interaction attempts at the orchestrator level
and provides escalation functionality when agents fail to get valid responses
after multiple attempts.
"""

import re
import json
import time
from typing import Dict, List, Any, Tuple
from datetime import datetime
from langchain.agents import Tool

from agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator import LoanAgentOrchestrator
from agentic_ai.modules.loan_processing.agents.user_interaction import UserInteractionAgent
from agentic_ai.modules.loan_processing.agents.human_agent import get_human_agent
from agentic_ai.core.utils.validators import is_pan, is_aadhaar


class EscalationOrchestrator(LoanAgentOrchestrator):
    """
    Enhanced orchestrator with escalation management.
    
    This orchestrator extends the base LoanAgentOrchestrator to add:
    - Attempt tracking at orchestrator level
    - Validation of user responses
    - Automatic escalation after 3 failed attempts
    - Human agent integration
    """
    
    def __init__(self, automate_user: bool = False, customer_profile=None, max_attempts: int = 3):
        # Initialize base orchestrator but with regular UserInteractionAgent
        # We'll handle escalation at this level
        super().__init__(automate_user, customer_profile)
        
        # Replace the interaction agent with regular one if not automated
        if not automate_user:
            self.interaction_agent = UserInteractionAgent()
        
        # Escalation tracking
        self.max_attempts = max_attempts
        self.attempt_tracker = {}  # Tracks attempts per question/context
        self.conversation_history = []
        self.human_agent = get_human_agent()
        
        # Override tools to add escalation support
        self.tools = self._setup_escalation_tools()
        self.agent_executor = self._create_escalation_executor()
    
    def _setup_escalation_tools(self):
        """Setup tools with escalation-aware UserInteraction."""
        base_tools = super()._setup_tools()
        
        # Replace UserInteraction tool with escalation-aware version
        escalation_tools = []
        for tool in base_tools:
            if tool.name == "UserInteraction":
                escalation_tools.append(Tool(
                    name="UserInteraction",
                    description="THE FIRST TOOL TO USE. Get user input with automatic escalation after 3 failed attempts. Input: question to ask the user. You MUST ask for loan purpose, loan amount, and city explicitly using separate questions.",
                    func=self._escalation_aware_user_interaction
                ))
            else:
                escalation_tools.append(tool)
        
        return escalation_tools
    
    def _escalation_aware_user_interaction(self, question: str) -> str:
        """
        User interaction with escalation support.
        
        This method:
        1. Tracks attempts per question context
        2. Validates responses based on question type
        3. Escalates to human after max attempts
        4. Prompts user before escalation
        """
        print(f"\n🤔 System Question: {question}")
        
        # Create a context key for this question
        context_key = self._create_context_key(question)
        
        # Initialize attempt counter for this context
        if context_key not in self.attempt_tracker:
            self.attempt_tracker[context_key] = {
                "question": question,
                "attempts": 0,
                "responses": [],
                "started_at": datetime.now().isoformat()
            }
        
        tracker = self.attempt_tracker[context_key]
        
        while tracker["attempts"] < self.max_attempts:
            tracker["attempts"] += 1
            
            print(f"🔄 Attempt {tracker['attempts']}/{self.max_attempts}")
            
            # Get user response
            user_response = input("Your response: ").strip()
            
            # Add to conversation history
            self.conversation_history.append(f"System: {question}")
            self.conversation_history.append(f"User: {user_response}")
            
            # Store response
            tracker["responses"].append({
                "attempt": tracker["attempts"],
                "response": user_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Validate response
            is_valid, validation_message = self._validate_response(question, user_response)
            
            if is_valid:
                print(f"✅ Valid response received")
                tracker["status"] = "success"
                tracker["completed_at"] = datetime.now().isoformat()
                return user_response
            else:
                print(f"⚠️ Invalid response: {validation_message}")
                
                if tracker["attempts"] < self.max_attempts:
                    print(f"🔄 Please try again. ({tracker['attempts']}/{self.max_attempts} attempts used)")
                    continue
                else:
                    # Max attempts reached - offer escalation
                    break
        
        # Max attempts reached - offer escalation
        return self._handle_escalation(context_key, question, tracker)
    
    def _create_context_key(self, question: str) -> str:
        """Create a unique context key for the question."""
        # Extract key words to create context
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["purpose", "use", "loan for"]):
            return "loan_purpose"
        elif any(word in question_lower for word in ["amount", "how much", "rupees"]):
            return "loan_amount"
        elif any(word in question_lower for word in ["city", "location", "where"]):
            return "user_city"
        elif any(word in question_lower for word in ["pan", "aadhaar", "identifier"]):
            return "user_identity"
        elif any(word in question_lower for word in ["salary", "income", "pdf", "document"]):
            return "salary_document"
        elif any(word in question_lower for word in ["update", "salary information"]):
            return "salary_update"
        else:
            # Generic context based on question hash
            return f"question_{abs(hash(question)) % 10000}"
    
    def _validate_response(self, question: str, response: str) -> Tuple[bool, str]:
        """
        Validate user response based on question type.
        
        Args:
            question: The question asked
            response: User's response
            
        Returns:
            Tuple of (is_valid, validation_message)
        """
        if not response or response.strip() == "":
            return False, "Empty response. Please provide a valid answer."
        
        question_lower = question.lower()
        response_lower = response.lower().strip()
        
        # Loan purpose validation
        if any(word in question_lower for word in ["purpose", "use", "loan for"]):
            if response_lower in ["i dont know", "why do you want", "unknown", "no", "nothing"]:
                return False, "Please specify a clear loan purpose (e.g., 'bike loan', 'home improvement', 'personal expenses')."
            if len(response.strip()) < 3:
                return False, "Please provide a more specific loan purpose."
            return True, "Valid loan purpose"
        
        # Loan amount validation
        elif any(word in question_lower for word in ["amount", "how much", "rupees"]):
            try:
                # Extract numbers from response
                numbers = re.findall(r'\d+', response)
                if not numbers:
                    return False, "Please provide a numeric loan amount."
                
                amount = int(''.join(numbers))
                
                # Check realistic range for loan amounts
                if amount < 1000:
                    return False, "Loan amount too small. Please provide an amount of at least ₹1,000."
                elif amount > 10000000:  # 1 crore
                    return False, "Loan amount too large. Please provide a realistic amount (typically under ₹1,00,00,000)."
                
                return True, f"Valid loan amount: ₹{amount:,}"
                
            except (ValueError, TypeError):
                return False, "Please provide a valid numeric amount."
        
        # City validation
        elif any(word in question_lower for word in ["city", "location", "where"]):
            if response_lower in ["unknown", "i dont know", "no", "nothing"]:
                return False, "Please provide your city name."
            if len(response.strip()) < 2:
                return False, "Please provide a valid city name."
            return True, "Valid city"
        
        # PAN/Aadhaar validation
        elif any(word in question_lower for word in ["pan", "aadhaar", "identifier"]):
            if is_pan(response):
                return True, "Valid PAN number"
            elif is_aadhaar(response):
                return True, "Valid Aadhaar number"
            else:
                return False, "Please provide a valid PAN (ABCDE1234F) or Aadhaar (12-digit number)."
        
        # Yes/No questions
        elif any(word in question_lower for word in ["yes", "no", "update", "want to"]):
            if response_lower in ["yes", "y", "no", "n", "yeah", "yep", "nope", "nah"]:
                return True, "Valid yes/no response"
            else:
                return False, "Please respond with 'yes' or 'no'."
        
        # Default validation - accept if not empty and reasonable length
        if len(response.strip()) >= 2:
            return True, "Valid response"
        else:
            return False, "Please provide a more detailed response."
    
    def _handle_escalation(self, context_key: str, question: str, tracker: Dict) -> str:
        """
        Handle escalation after max attempts reached.
        
        Args:
            context_key: Unique context identifier
            question: The question that failed
            tracker: Attempt tracking data
            
        Returns:
            Final response (escalated or user choice)
        """
        print(f"\n{'='*60}")
        print("🚨 MAXIMUM ATTEMPTS REACHED")
        print(f"{'='*60}")
        print(f"❓ Question: {question}")
        print(f"🔢 Attempts made: {tracker['attempts']}")
        print(f"📝 Your responses: {[r['response'] for r in tracker['responses']]}")
        print(f"{'='*60}")
        
        # Ask user if they want to escalate
        while True:
            escalate_choice = input(
                "\n🤔 Would you like to escalate this to a human agent for assistance? (yes/no): "
            ).strip().lower()
            
            if escalate_choice in ["yes", "y", "yeah", "yep"]:
                print("\n🚀 Escalating to human agent...")
                return self._escalate_to_human(context_key, question, tracker)
            
            elif escalate_choice in ["no", "n", "nope", "nah"]:
                print("\n🔄 Let's try again with the same question.")
                
                # Give user one more chance with guidance
                print(f"\n💡 Helpful tip: {self._get_guidance_for_question(question)}")
                
                final_response = input(f"Your response: ").strip()
                
                # Accept whatever they provide this time
                if final_response:
                    tracker["final_response"] = final_response
                    tracker["status"] = "completed_without_escalation"
                    tracker["completed_at"] = datetime.now().isoformat()
                    return final_response
                else:
                    return "Unable to process request"
            
            else:
                print("⚠️ Please respond with 'yes' or 'no'.")
    
    def _get_guidance_for_question(self, question: str) -> str:
        """Provide helpful guidance based on question type."""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["purpose", "use", "loan for"]):
            return "Example answers: 'bike loan', 'home renovation', 'personal expenses', 'medical emergency'"
        
        elif any(word in question_lower for word in ["amount", "how much", "rupees"]):
            return "Example: '50000' or 'fifty thousand rupees' (provide a realistic amount between ₹1,000 and ₹10,00,000)"
        
        elif any(word in question_lower for word in ["city", "location", "where"]):
            return "Example: 'Mumbai', 'Delhi', 'Bangalore' (provide your current city name)"
        
        elif any(word in question_lower for word in ["pan", "aadhaar", "identifier"]):
            return "PAN format: ABCDE1234F, Aadhaar format: 123456789012 (12 digits)"
        
        else:
            return "Please provide a clear and specific answer to the question."
    
    def _escalate_to_human(self, context_key: str, question: str, tracker: Dict) -> str:
        """
        Escalate to human agent.
        
        Args:
            context_key: Context identifier
            question: Failed question
            tracker: Attempt tracking data
            
        Returns:
            Human agent response
        """
        # Prepare escalation context
        escalation_context = {
            "agent_name": "UserInteractionAgent",
            "user_input": tracker["responses"][-1]["response"] if tracker["responses"] else "",
            "question": question,
            "failure_count": tracker["attempts"],
            "conversation_history": self.conversation_history.copy(),
            "context_key": context_key,
            "all_responses": [r["response"] for r in tracker["responses"]],
            "escalated_at": datetime.now().isoformat()
        }
        
        # Update tracker
        tracker["status"] = "escalated"
        tracker["escalated_at"] = datetime.now().isoformat()
        
        # Call human agent
        human_response = self.human_agent.escalate_to_human(escalation_context)
        
        # Update tracker with human response
        tracker["human_response"] = human_response
        tracker["completed_at"] = datetime.now().isoformat()
        
        return human_response
    
    def _create_escalation_executor(self):
        """Create agent executor with escalation support."""
        return self.agent_executor
    
    def get_escalation_statistics(self) -> Dict[str, Any]:
        """Get escalation statistics for this session."""
        total_contexts = len(self.attempt_tracker)
        escalated_contexts = sum(1 for t in self.attempt_tracker.values() if t.get("status") == "escalated")
        successful_contexts = sum(1 for t in self.attempt_tracker.values() if t.get("status") == "success")
        
        return {
            "total_interactions": total_contexts,
            "successful_interactions": successful_contexts,
            "escalated_interactions": escalated_contexts,
            "escalation_rate": escalated_contexts / total_contexts if total_contexts > 0 else 0,
            "average_attempts": sum(t["attempts"] for t in self.attempt_tracker.values()) / total_contexts if total_contexts > 0 else 0,
            "contexts": self.attempt_tracker.copy()
        }
    
    def process_application(self, user_input: str) -> str:
        """Process loan application with escalation support."""
        print(f"\n🚀 Starting loan application with escalation support...")
        print(f"📊 Max attempts per question: {self.max_attempts}")
        print(f"🤖 Escalation available if needed")
        
        # Call parent's process_application
        result = super().process_application(user_input)
        
        # Print escalation summary
        stats = self.get_escalation_statistics()
        if stats["total_interactions"] > 0:
            print(f"\n📊 SESSION SUMMARY:")
            print(f"   Total interactions: {stats['total_interactions']}")
            print(f"   Successful: {stats['successful_interactions']}")
            print(f"   Escalated: {stats['escalated_interactions']}")
            print(f"   Average attempts: {stats['average_attempts']:.1f}")
        
        return result
