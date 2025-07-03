import json
import time
from typing import Any, Dict, List, Callable
from datetime import datetime
from agentic_ai.modules.loan_processing.agents.human_agent import get_human_agent

class EscalationManager:
    """
    Manages automatic retry logic and escalation to human agents when
    automated agents fail to process user input properly.
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.failure_history = {}
        self.human_agent = get_human_agent()
        
    def execute_with_escalation(self, 
                              agent_func: Callable,
                              agent_name: str,
                              user_input: str,
                              question: str,
                              conversation_history: List[str] = None,
                              validation_func: Callable = None) -> str:
        """
        Execute an agent function with automatic retry and human escalation.
        
        Args:
            agent_func: The agent function to execute
            agent_name: Name of the agent for tracking
            user_input: The user's input
            question: The question being asked
            conversation_history: Previous conversation context
            validation_func: Optional function to validate the response
            
        Returns:
            Agent response or human escalation response
        """
        session_key = f"{agent_name}_{int(time.time())}"
        attempt_count = 0
        
        if conversation_history is None:
            conversation_history = []
            
        while attempt_count < self.max_retries:
            try:
                attempt_count += 1
                print(f"\n🔄 Attempt {attempt_count}/{self.max_retries} - {agent_name}")
                
                # Execute the agent function
                response = agent_func(user_input)
                
                # Validate the response if validation function provided
                if validation_func:
                    is_valid, validation_message = validation_func(response, user_input)
                    if not is_valid:
                        print(f"⚠️ Response validation failed: {validation_message}")
                        if attempt_count < self.max_retries:
                            print(f"🔄 Retrying... ({attempt_count}/{self.max_retries})")
                            time.sleep(1)  # Brief delay before retry
                            continue
                        else:
                            # Max retries reached, escalate
                            break
                
                # Check for common failure indicators
                if self._is_failure_response(response):
                    print(f"⚠️ Detected failure response from {agent_name}")
                    if attempt_count < self.max_retries:
                        print(f"🔄 Retrying... ({attempt_count}/{self.max_retries})")
                        time.sleep(1)
                        continue
                    else:
                        # Max retries reached, escalate
                        break
                
                # Success - record and return
                print(f"✅ {agent_name} succeeded on attempt {attempt_count}")
                self._record_success(session_key, agent_name, attempt_count)
                return response
                
            except Exception as e:
                print(f"❌ {agent_name} failed on attempt {attempt_count}: {str(e)}")
                if attempt_count < self.max_retries:
                    print(f"🔄 Retrying... ({attempt_count}/{self.max_retries})")
                    time.sleep(1)
                    continue
                else:
                    # Max retries reached, escalate
                    break
        
        # If we reach here, all retries failed - escalate to human
        print(f"🚨 {agent_name} failed after {self.max_retries} attempts - escalating to human")
        return self._escalate_to_human(
            agent_name=agent_name,
            user_input=user_input,
            question=question,
            failure_count=attempt_count,
            conversation_history=conversation_history,
            session_key=session_key
        )
    
    def _is_failure_response(self, response: str) -> bool:
        """
        Check if a response indicates a failure that should trigger retry.
        
        Args:
            response: The agent's response
            
        Returns:
            True if the response indicates failure
        """
        if not response:
            return True
            
        failure_indicators = [
            "error occurred",
            "failed to process",
            "could not understand",
            "invalid input",
            "parsing error",
            "llm parsing for identifier failed",
            "chain error",
            "timeout",
            "connection error",
            "service unavailable"
        ]
        
        response_lower = response.lower()
        for indicator in failure_indicators:
            if indicator in response_lower:
                return True
                
        # Check for JSON error responses
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict) and "error" in parsed:
                return True
        except:
            pass
            
        return False
    
    def _escalate_to_human(self, 
                          agent_name: str,
                          user_input: str,
                          question: str,
                          failure_count: int,
                          conversation_history: List[str],
                          session_key: str) -> str:
        """
        Escalate the failed interaction to a human agent.
        
        Args:
            agent_name: Name of the failed agent
            user_input: User's input
            question: Question that couldn't be processed
            failure_count: Number of failed attempts
            conversation_history: Previous conversation
            session_key: Unique session identifier
            
        Returns:
            Human agent response
        """
        # Record the failure
        self._record_failure(session_key, agent_name, failure_count)
        
        # Prepare escalation context
        escalation_context = {
            "agent_name": agent_name,
            "user_input": user_input,
            "question": question,
            "failure_count": failure_count,
            "conversation_history": conversation_history,
            "session_key": session_key,
            "escalated_at": datetime.now().isoformat()
        }
        
        # Escalate to human agent
        human_response = self.human_agent.escalate_to_human(escalation_context)
        
        return human_response
    
    def _record_success(self, session_key: str, agent_name: str, attempt_count: int):
        """Record a successful agent interaction."""
        if session_key not in self.failure_history:
            self.failure_history[session_key] = []
            
        self.failure_history[session_key].append({
            "agent_name": agent_name,
            "status": "success",
            "attempt_count": attempt_count,
            "timestamp": datetime.now().isoformat()
        })
    
    def _record_failure(self, session_key: str, agent_name: str, failure_count: int):
        """Record a failed agent interaction."""
        if session_key not in self.failure_history:
            self.failure_history[session_key] = []
            
        self.failure_history[session_key].append({
            "agent_name": agent_name,
            "status": "failed",
            "failure_count": failure_count,
            "escalated": True,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get statistics about agent failures and escalations."""
        total_sessions = len(self.failure_history)
        total_failures = sum(1 for session in self.failure_history.values() 
                           for event in session if event["status"] == "failed")
        total_successes = sum(1 for session in self.failure_history.values() 
                            for event in session if event["status"] == "success")
        
        agent_failure_counts = {}
        for session in self.failure_history.values():
            for event in session:
                agent_name = event["agent_name"]
                if agent_name not in agent_failure_counts:
                    agent_failure_counts[agent_name] = {"failures": 0, "successes": 0}
                
                if event["status"] == "failed":
                    agent_failure_counts[agent_name]["failures"] += 1
                else:
                    agent_failure_counts[agent_name]["successes"] += 1
        
        return {
            "total_sessions": total_sessions,
            "total_failures": total_failures,
            "total_successes": total_successes,
            "escalation_rate": total_failures / (total_failures + total_successes) if (total_failures + total_successes) > 0 else 0,
            "agent_statistics": agent_failure_counts
        }

# Global instance for easy access
_escalation_manager_instance = None

def get_escalation_manager():
    """Get the global EscalationManager instance."""
    global _escalation_manager_instance
    if _escalation_manager_instance is None:
        _escalation_manager_instance = EscalationManager()
    return _escalation_manager_instance
