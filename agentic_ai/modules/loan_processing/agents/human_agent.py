
import time
import threading
import queue
import json
import os
from datetime import datetime
from agentic_ai.core.agent.base_agent import BaseAgent
 
class HumanAgent(BaseAgent):
    """
    Human escalation agent that can connect to a human operator for complex cases.
   
    This agent is triggered when automated agents fail to process user input properly
    after multiple attempts. It provides a way for human operators to intervene and
    provide appropriate responses.
    """
   
    def __init__(self):
        super().__init__()
        self.escalation_queue = queue.Queue()
       
        # Use file-based storage for sharing between processes
        # Use absolute path to ensure both dashboard and streamlit app use same directory
        # Find the project root (where requirements.txt is located)
        current_file = os.path.abspath(__file__)
        project_root = current_file
        while project_root != os.path.dirname(project_root):  # Stop at filesystem root
            if os.path.exists(os.path.join(project_root, 'requirements.txt')):
                break
            project_root = os.path.dirname(project_root)
       
        self.storage_dir = os.path.join(project_root, "escalation_data")
        self.active_sessions_file = os.path.join(self.storage_dir, "active_sessions.json")
        self.human_responses_file = os.path.join(self.storage_dir, "human_responses.json")
       
        # Create storage directory if it doesn't exist
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
           
        # Initialize storage files if they don't exist
        if not os.path.exists(self.active_sessions_file):
            self._save_active_sessions({})
        if not os.path.exists(self.human_responses_file):
            self._save_human_responses({})
   
    def _load_active_sessions(self) -> dict:
        """Load active sessions from file."""
        try:
            with open(self.active_sessions_file, 'r') as f:
                return json.load(f)
        except:
            return {}
   
    def _save_active_sessions(self, sessions: dict):
        """Save active sessions to file."""
        try:
            with open(self.active_sessions_file, 'w') as f:
                json.dump(sessions, f, indent=2)
        except Exception as e:
            print(f"Error saving active sessions: {e}")
   
    def _load_human_responses(self) -> dict:
        """Load human responses from file."""
        try:
            with open(self.human_responses_file, 'r') as f:
                return json.load(f)
        except:
            return {}
   
    def _save_human_responses(self, responses: dict):
        """Save human responses to file."""
        try:
            with open(self.human_responses_file, 'w') as f:
                json.dump(responses, f, indent=2)
        except Exception as e:
            print(f"Error saving human responses: {e}")
       
    def escalate_to_human(self, context: dict) -> str:
        """
        Escalate a user interaction to a human operator.
       
        Args:
            context: Dictionary containing:
                - user_input: The user's original input
                - agent_name: Name of the agent that failed
                - failure_count: Number of failed attempts
                - conversation_history: Previous conversation context
                - question: The question that couldn't be processed
               
        Returns:
            Human operator's response or timeout message
        """
        escalation_id = f"esc_{int(time.time())}_{len(self._load_active_sessions())}"
       
        escalation_data = {
            "escalation_id": escalation_id,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "status": "waiting_for_human",
            "priority": self._calculate_priority(context)
        }
       
        print(f"\n{'='*60}")
        print("🚨 ESCALATION TO HUMAN OPERATOR")
        print(f"{'='*60}")
        print(f"🆔 Escalation ID: {escalation_id}")
        print(f"🤖 Failed Agent: {context.get('agent_name', 'Unknown')}")
        print(f"🔢 Attempt Count: {context.get('failure_count', 0)}")
        print(f"❓ Question: {context.get('question', 'N/A')}")
        print(f"👤 User Input: {context.get('user_input', 'N/A')}")
        print(f"📈 Priority: {escalation_data['priority']}")
        print(f"{'='*60}")
       
        # Store the escalation
        active_sessions = self._load_active_sessions()
        active_sessions[escalation_id] = escalation_data
        self._save_active_sessions(active_sessions)
       
        # Wait for human response with timeout
        human_response = self._wait_for_human_response(escalation_id)
       
        return human_response
   
    def _calculate_priority(self, context: dict) -> str:
        """Calculate escalation priority based on context."""
        failure_count = context.get('failure_count', 0)
        agent_name = context.get('agent_name', '')
       
        if failure_count >= 5:
            return "HIGH"
        elif failure_count >= 3:
            return "MEDIUM"
        elif 'DataQuery' in agent_name or 'RiskAssessment' in agent_name:
            return "MEDIUM"
        else:
            return "LOW"
   
    def _wait_for_human_response(self, escalation_id: str, timeout: int = 300) -> str:
        """
        Wait for human operator response with timeout.
       
        Args:
            escalation_id: Unique escalation identifier
            timeout: Timeout in seconds (default 5 minutes)
           
        Returns:
            Human response or timeout message
        """
        print(f"\n⏳ Waiting for human operator response (timeout: {timeout}s)...")
        print(f"📞 Human operators can respond via the admin interface")
        print(f"🔗 Or call provide_human_response('{escalation_id}', 'your_response')")
       
        # In a real implementation, this would connect to a web interface,
        # chat system, or notification system for human operators
       
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if human has provided a response
            human_responses = self._load_human_responses()
            if escalation_id in human_responses:
                response = human_responses.pop(escalation_id)
                self._save_human_responses(human_responses)
               
                # Update session status
                active_sessions = self._load_active_sessions()
                if escalation_id in active_sessions:
                    active_sessions[escalation_id]['status'] = 'resolved'
                    active_sessions[escalation_id]['human_response'] = response
                    active_sessions[escalation_id]['resolved_at'] = datetime.now().isoformat()
                    self._save_active_sessions(active_sessions)
               
                # Format timestamp for display: 'Jul 01, 2025, 05:41 PM'
                if isinstance(response, dict) and 'timestamp' in response:
                    try:
                        iso_time = response['timestamp']
                        formatted_time = datetime.fromisoformat(iso_time).strftime('%b %d, %Y, %I:%M %p')
                        response['timestamp'] = formatted_time
                    except Exception as ex:
                        pass
                print(f"\n✅ Human operator responded: {response}")
                return response
           
            # For demo purposes, provide a way to simulate human input
            # In production, this would be replaced with actual human interface
            if self._check_for_demo_input():
                break
               
            time.sleep(1)
       
        # Timeout occurred
        timeout_response = "I apologize, but our human operator is currently unavailable. Please try again later or contact our customer service directly."
       
        # Update session status for timeout
        active_sessions = self._load_active_sessions()
        if escalation_id in active_sessions:
            active_sessions[escalation_id]['status'] = 'timeout'
            active_sessions[escalation_id]['timeout_at'] = datetime.now().isoformat()
            self._save_active_sessions(active_sessions)
       
        print(f"\n⏰ Timeout: No human response received within {timeout} seconds")
        return timeout_response
   
    def _check_for_demo_input(self) -> bool:
        """
        For demo purposes, check if user wants to provide human response.
        In production, this would be replaced with actual operator interface.
        """
        try:
            # Simplified demo input check (Windows compatible)
            import sys
            import os
           
            # For Windows, we'll use a different approach
            if os.name == 'nt':  # Windows
                # Check if there's input available (non-blocking)
                import msvcrt
                if msvcrt.kbhit():
                    line = input().strip()
                    if line.startswith("HUMAN_RESPONSE:"):
                        response = line.replace("HUMAN_RESPONSE:", "").strip()
                        active_sessions = self._load_active_sessions()
                        if active_sessions:
                            latest_escalation_id = max(active_sessions.keys())
                            human_responses = self._load_human_responses()
                            human_responses[latest_escalation_id] = response
                            self._save_human_responses(human_responses)
                            return True
                return False
            else:
                # Unix/Linux systems can use select
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    user_input = input().strip()
                    if user_input.startswith("HUMAN_RESPONSE:"):
                        response = user_input.replace("HUMAN_RESPONSE:", "").strip()
                        active_sessions = self._load_active_sessions()
                        if active_sessions:
                            latest_escalation_id = max(active_sessions.keys())
                            human_responses = self._load_human_responses()
                            human_responses[latest_escalation_id] = response
                            self._save_human_responses(human_responses)
                            return True
                return False
        except:
            # Fallback - no input available
            return False
   
    def provide_human_response(self, escalation_id: str, response: str) -> bool:
        """
        Provide a human response for a specific escalation.
        This method would be called by the human operator interface.
       
        Args:
            escalation_id: The escalation ID to respond to
            response: The human operator's response
           
        Returns:
            True if successful, False if escalation not found
        """
        active_sessions = self._load_active_sessions()
        if escalation_id in active_sessions:
            human_responses = self._load_human_responses()
            human_responses[escalation_id] = response
            self._save_human_responses(human_responses)
            print(f"✅ Human response recorded for escalation {escalation_id}")
            return True
        else:
            print(f"❌ Escalation {escalation_id} not found")
            return False
   
    def get_active_escalations(self) -> dict:
        """Get all active escalations for human operator dashboard."""
        active_sessions = self._load_active_sessions()
        active = {k: v for k, v in active_sessions.items()
                 if v['status'] == 'waiting_for_human'}
        return active
   
    def get_escalation_history(self) -> dict:
        """Get escalation history for analysis and reporting."""
        return self._load_active_sessions()
   
    def run(self, query: str) -> str:
        """
        Handle human escalation requests.
       
        Args:
            query: JSON string containing escalation context
           
        Returns:
            Human operator response
        """
        try:
            context = json.loads(query)
            return self.escalate_to_human(context)
        except Exception as e:
            return f"Error processing human escalation: {str(e)}"
 
# Global instance for easy access
_human_agent_instance = None
 
def get_human_agent():
    """Get the global HumanAgent instance."""
    global _human_agent_instance
    if _human_agent_instance is None:
        _human_agent_instance = HumanAgent()
    return _human_agent_instance
 
 