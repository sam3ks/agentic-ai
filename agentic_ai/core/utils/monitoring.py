import time
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class WorkflowMonitor:
    """Monitor and track workflow execution for reliability analysis."""
    
    def __init__(self, log_file: str = "workflow_monitor.log"):
        self.log_file = log_file
        self.current_session = None
        self.session_start_time = None
        self.steps_completed = []
        self.errors_encountered = []
        
    def start_session(self, session_id: str, user_input: str) -> None:
        """Start a new workflow session."""
        self.current_session = session_id
        self.session_start_time = time.time()
        self.steps_completed = []
        self.errors_encountered = []
        
        self._log_event("SESSION_START", {
            "session_id": session_id,
            "user_input": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
    def log_step(self, step_name: str, status: str, details: Dict[str, Any] = None) -> None:
        """Log a workflow step."""
        step_data = {
            "step_name": step_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        self.steps_completed.append(step_data)
        self._log_event("STEP", step_data)
        
    def log_error(self, error_type: str, error_message: str, step_name: str = None) -> None:
        """Log an error occurrence."""
        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "step_name": step_name,
            "timestamp": datetime.now().isoformat()
        }
        
        self.errors_encountered.append(error_data)
        self._log_event("ERROR", error_data)
        
    def log_retry(self, operation: str, attempt: int, max_attempts: int) -> None:
        """Log a retry attempt."""
        retry_data = {
            "operation": operation,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "timestamp": datetime.now().isoformat()
        }
        
        self._log_event("RETRY", retry_data)
        
    def end_session(self, final_status: str, final_output: str = None) -> Dict[str, Any]:
        """End the current session and return summary."""
        if not self.current_session:
            return {}
            
        end_time = time.time()
        duration = end_time - self.session_start_time
        
        summary = {
            "session_id": self.current_session,
            "duration_seconds": duration,
            "final_status": final_status,
            "steps_completed": len(self.steps_completed),
            "errors_encountered": len(self.errors_encountered),
            "success": final_status == "SUCCESS",
            "final_output_length": len(final_output) if final_output else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        self._log_event("SESSION_END", summary)
        
        # Reset session
        self.current_session = None
        self.session_start_time = None
        
        return summary
        
    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Write event to log file."""
        try:
            log_entry = {
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            print(f"[MONITOR] Failed to write log: {e}")
            
    def get_failure_statistics(self, last_n_sessions: int = 10) -> Dict[str, Any]:
        """Analyze recent failures to identify patterns."""
        try:
            if not os.path.exists(self.log_file):
                return {"error": "No log file found"}
                
            sessions = []
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry["event_type"] == "SESSION_END":
                            sessions.append(entry["data"])
                    except:
                        continue
                        
            # Get last N sessions
            recent_sessions = sessions[-last_n_sessions:] if len(sessions) >= last_n_sessions else sessions
            
            if not recent_sessions:
                return {"error": "No recent sessions found"}
                
            # Calculate statistics
            total_sessions = len(recent_sessions)
            successful_sessions = sum(1 for s in recent_sessions if s.get("success", False))
            failed_sessions = total_sessions - successful_sessions
            
            avg_duration = sum(s.get("duration_seconds", 0) for s in recent_sessions) / total_sessions
            
            return {
                "total_sessions": total_sessions,
                "successful_sessions": successful_sessions,
                "failed_sessions": failed_sessions,
                "success_rate": (successful_sessions / total_sessions) * 100,
                "average_duration": avg_duration,
                "recent_failures": [s for s in recent_sessions if not s.get("success", False)]
            }
            
        except Exception as e:
            return {"error": f"Failed to analyze statistics: {e}"}

# Global monitor instance
monitor = WorkflowMonitor()
