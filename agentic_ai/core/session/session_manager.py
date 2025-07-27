"""
Session Management Module for Loan Processing
Provides persistent session state that survives interruptions
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import atexit

class SessionManager:
    """Manages persistent session state for loan applications"""
    
    def __init__(self, session_dir: str = "session_data"):
        self.session_dir = session_dir
        self.session_id = None
        self.session_file = None
        self.state = {}
        self.lock = threading.Lock()
        
        # Ensure session directory exists
        os.makedirs(session_dir, exist_ok=True)
        
        # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)
    
    def start_session(self, initial_user_request: str = None) -> str:
        """Start a new session or resume an existing one"""
        with self.lock:
            # Check for existing session to resume - but only if it's not completed
            existing_session = self._find_resumable_session()
            
            if existing_session:
                self.session_id = existing_session
                self.session_file = os.path.join(self.session_dir, f"{self.session_id}.json")
                self.state = self._load_session()
                print(f"📋 Resuming session: {self.session_id}")
                return self.session_id
            
            # Create new session
            self.session_id = f"loan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            self.session_file = os.path.join(self.session_dir, f"{self.session_id}.json")
            
            self.state = {
                "session_id": self.session_id,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "user_request": initial_user_request,
                "workflow_step": 0,
                "collected_data": {},
                "conversation_history": [],
                "agent_state": {},
                "orchestrator_state": {},
                "last_updated": datetime.now().isoformat()
            }
            
            self._save_session()
            print(f"🆕 New session started: {self.session_id}")
            return self.session_id

    def start_fresh_session(self, initial_user_request: str = None) -> str:
        """Force start a completely new session, ignoring any existing sessions"""
        with self.lock:
            # Clear any existing session reference
            self.session_id = None
            self.session_file = None
            self.state = {}
            
            # Create new session
            self.session_id = f"loan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            self.session_file = os.path.join(self.session_dir, f"{self.session_id}.json")
            
            self.state = {
                "session_id": self.session_id,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "user_request": initial_user_request,
                "workflow_step": 0,
                "collected_data": {},
                "conversation_history": [],
                "agent_state": {},
                "orchestrator_state": {},
                "last_updated": datetime.now().isoformat()
            }
            
            self._save_session()
            print(f"🆕 New session started: {self.session_id}")
            return self.session_id
    
    def update_state(self, key: str, value: Any):
        """Update a specific state value"""
        with self.lock:
            if self.session_id:
                self.state[key] = value
                self.state["last_updated"] = datetime.now().isoformat()
                self._save_session()
    
    def get_state(self, key: str, default=None):
        """Get a specific state value"""
        with self.lock:
            return self.state.get(key, default)
    
    def set_workflow_step(self, step: int, step_description: str = None):
        """Update current workflow step"""
        with self.lock:
            self.state["workflow_step"] = step
            if step_description:
                self.state["current_step_description"] = step_description
            self.state["last_updated"] = datetime.now().isoformat()
            self._save_session()
    
    def add_conversation_entry(self, speaker: str, message: str):
        """Add entry to conversation history"""
        with self.lock:
            if "conversation_history" not in self.state:
                self.state["conversation_history"] = []
            
            self.state["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "speaker": speaker,
                "message": message
            })
            self.state["last_updated"] = datetime.now().isoformat()
            self._save_session()
    
    def update_collected_data(self, data_type: str, value: Any):
        """Update collected user data"""
        with self.lock:
            if "collected_data" not in self.state:
                self.state["collected_data"] = {}
            
            self.state["collected_data"][data_type] = value
            self.state["last_updated"] = datetime.now().isoformat()
            self._save_session()
    
    def update_agent_state(self, agent_name: str, agent_state: Dict):
        """Update specific agent's state"""
        with self.lock:
            if "agent_state" not in self.state:
                self.state["agent_state"] = {}
            
            self.state["agent_state"][agent_name] = agent_state
            self.state["last_updated"] = datetime.now().isoformat()
            self._save_session()
    
    def update_orchestrator_state(self, orchestrator_state: Dict):
        """Update orchestrator state"""
        with self.lock:
            self.state["orchestrator_state"] = orchestrator_state
            self.state["last_updated"] = datetime.now().isoformat()
            self._save_session()
    
    def complete_session(self, final_result: str = None):
        """Mark session as completed"""
        with self.lock:
            self.state["status"] = "completed"
            self.state["completed_at"] = datetime.now().isoformat()
            if final_result:
                self.state["final_result"] = final_result
            self._save_session()
            print(f"✅ Session completed: {self.session_id}")
    
    def list_sessions(self) -> list:
        """List all available sessions"""
        sessions = []
        for file in os.listdir(self.session_dir):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(self.session_dir, file), 'r') as f:
                        session_data = json.load(f)
                        sessions.append({
                            "session_id": session_data.get("session_id"),
                            "created_at": session_data.get("created_at"),
                            "status": session_data.get("status"),
                            "user_request": session_data.get("user_request", "")[:50] + "...",
                            "workflow_step": session_data.get("workflow_step", 0)
                        })
                except:
                    continue
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)
    
    def resume_session(self, session_id: str) -> bool:
        """Resume a specific session"""
        session_file = os.path.join(self.session_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            with self.lock:
                self.session_id = session_id
                self.session_file = session_file
                self.state = self._load_session()
                
                # Check if session is already completed or ended by user
                session_status = self.state.get("status", "active")
                if session_status == "completed":
                    print(f"❌ Cannot resume session {session_id}: Session already completed")
                    print(f"📋 Session was finished successfully. Please start a new loan application.")
                    return False
                elif session_status == "ended_by_user":
                    print(f"❌ Cannot resume session {session_id}: Session was ended by user")
                    print(f"🚪 User declined escalation and ended the loan application. Please start a new loan application.")
                    return False
                
                print(f"📋 Resumed session: {session_id}")
                return True
        return False
    
    def get_session_status(self, session_id: str = None) -> str:
        """Get the status of a session (active, completed, etc.)"""
        if session_id:
            # Check specific session
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                        return session_data.get("status", "active")
                except:
                    return "error"
            return "not_found"
        else:
            # Get status of current session
            return self.state.get("status", "active")
    
    def is_session_completed(self, session_id: str = None) -> bool:
        """Check if a session is completed"""
        return self.get_session_status(session_id) == "completed"
    
    def _find_resumable_session(self) -> Optional[str]:
        """Find the most recent active session to resume"""
        for file in sorted(os.listdir(self.session_dir), reverse=True):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(self.session_dir, file), 'r') as f:
                        session_data = json.load(f)
                        if session_data.get("status") == "active":
                            return session_data.get("session_id")
                except:
                    continue
        return None
    
    def _load_session(self) -> Dict:
        """Load session from file"""
        try:
            with open(self.session_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_session(self):
        """Save session to file"""
        if self.session_file:
            try:
                with open(self.session_file, 'w') as f:
                    json.dump(self.state, f, indent=2, default=str)
            except Exception as e:
                print(f"Warning: Could not save session: {e}")
    
    def _cleanup_on_exit(self):
        """Cleanup on process exit"""
        if self.session_id and self.state.get("status") == "active":
            # Mark as interrupted if still active
            self.state["status"] = "interrupted"
            self.state["interrupted_at"] = datetime.now().isoformat()
            self._save_session()

# Global session manager instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
