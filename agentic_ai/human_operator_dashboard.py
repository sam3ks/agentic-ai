"""
Human Operator Dashboard for handling escalated loan processing cases.

This script provides a command-line interface for human operators to:
1. View active escalations
2. Respond to escalated cases
3. Monitor escalation statistics
4. View conversation history

Usage:
    python human_operator_dashboard.py
"""

import time
import json
from datetime import datetime
from agentic_ai.modules.loan_processing.agents.human_agent import get_human_agent
from agentic_ai.modules.loan_processing.agents.escalation_manager import get_escalation_manager

class HumanOperatorDashboard:
    """Dashboard for human operators to handle escalations."""
    
    def __init__(self):
        self.human_agent = get_human_agent()
        self.escalation_manager = get_escalation_manager()
        self.running = True
        
    def run(self):
        """Main dashboard loop."""
        print("🎯 HUMAN OPERATOR DASHBOARD")
        print("=" * 50)
        print("Welcome to the loan processing escalation dashboard!")
        print("This interface allows you to handle cases that automated agents couldn't process.")
        print()
        
        while self.running:
            self._show_main_menu()
            choice = input("\nEnter your choice (1-2): ").strip()
            
            if choice == "1":
                self._view_active_escalations()
            elif choice == "2":
                self._respond_to_escalation()
            elif choice == "3":
                self._view_escalation_history()
            else:
                print("❌ Invalid choice. Please enter 1-2.")
                
    def _show_main_menu(self):
        """Display the main menu."""
        print("\n📋 MAIN MENU")
        print("-" * 30)
        print("1. 👀 View Active Escalations")
        print("2. 💬 Respond to Escalation")
        
    def _view_active_escalations(self):
        """Display all active escalations waiting for human response."""
        print("\n🚨 ACTIVE ESCALATIONS")
        print("=" * 50)
        
        active_escalations = self.human_agent.get_active_escalations()
        
        if not active_escalations:
            print("✅ No active escalations at this time.")
            return
        
        for escalation_id, escalation in active_escalations.items():
            context = escalation['context']
            # Minimal change: format timestamp for display (12-hour format with AM/PM)
            try:
                friendly_time = datetime.fromisoformat(escalation['timestamp']).strftime('%d %b %Y, %I:%M:%S %p')
            except Exception:
                friendly_time = escalation['timestamp']
            print(f"\n🆔 ID: {escalation_id}")
            print(f"⏰ Time: {friendly_time}")
            print(f"📈 Priority: {escalation['priority']}")
            print(f"🤖 Failed Agent: {context.get('agent_name', 'Unknown')}")
            print(f"🔢 Attempts: {context.get('failure_count', 0)}")
            print(f"❓ Question: {context.get('question', 'N/A')}")
            print(f"👤 User Input: {context.get('user_input', 'N/A')}")
            
            # Show conversation history if available
            history = context.get('conversation_history', [])
            if history:
                print(f"📜 Recent Conversation:")
                for i, msg in enumerate(history[-3:]):  # Show last 3 messages
                    print(f"   {i+1}. {msg}")
            print("-" * 50)
            
    def _respond_to_escalation(self):
        """Allow operator to respond to a specific escalation."""
        print("\n💬 RESPOND TO ESCALATION")
        print("=" * 50)
        
        active_escalations = self.human_agent.get_active_escalations()
        
        if not active_escalations:
            print("✅ No active escalations to respond to.")
            return
            
        # Show available escalations
        print("Available escalations:")
        for i, (escalation_id, escalation) in enumerate(active_escalations.items(), 1):
            context = escalation['context']
            print(f"{i}. {escalation_id} - {context.get('agent_name', 'Unknown')} - Priority: {escalation['priority']}")
            
        try:
            choice = int(input(f"\nSelect escalation (1-{len(active_escalations)}): ")) - 1
            escalation_items = list(active_escalations.items())
            
            if 0 <= choice < len(escalation_items):
                escalation_id, escalation = escalation_items[choice]
                self._handle_escalation_response(escalation_id, escalation)
            else:
                print("❌ Invalid selection.")
                
        except ValueError:
            print("❌ Please enter a valid number.")
            
    def _handle_escalation_response(self, escalation_id: str, escalation: dict):
        """Handle response to a specific escalation."""
        context = escalation['context']
        
        print(f"\n🎯 ESCALATION DETAILS: {escalation_id}")
        print("=" * 50)
        # Show escalation time in a user-friendly 12-hour format with AM/PM
        try:
            friendly_time = datetime.fromisoformat(escalation['timestamp']).strftime('%d %b %Y, %I:%M:%S %p')
        except Exception:
            friendly_time = escalation.get('timestamp', 'N/A')
        print(f"⏰ Time: {friendly_time}")
        print(f"🤖 Failed Agent: {context.get('agent_name', 'Unknown')}")
        print(f"❓ Question: {context.get('question', 'N/A')}")
        print(f"👤 User Input: {context.get('user_input', 'N/A')}")
        print(f"🔢 Failed Attempts: {context.get('failure_count', 0)}")
        
        # Show conversation history
        history = context.get('conversation_history', [])
        if history:
            print(f"\n📜 FULL CONVERSATION HISTORY:")
            for i, msg in enumerate(history, 1):
                print(f"   {i}. {msg}")
                
        print("\n" + "=" * 50)
        print("💡 RESPONSE GUIDELINES:")
        print("- Provide a clear, helpful response")
        print("- Address the specific issue the user is facing")
        print("- Use simple, professional language")
        print("- If technical issue, suggest alternative approaches")
        print("=" * 50)
        
        while True:
            response = input("\n✏️ Enter your response (or 'cancel' to abort): ")
            if response.lower() == 'cancel':
                print("🚫 Response cancelled.")
                return
            
            # Validate response (basic check)
            if len(response) < 3:
                print("❌ Response too short. Please provide a more detailed answer.")
                continue
            
            # Log the response (for auditing, etc.)
            print(f"📥 Logging response: {response}")
            # Here you would typically call a logging function or save to a file
            
            # Send the response back through the escalation manager
            result = self.escalation_manager.process_human_response(escalation_id, response)
            
            if result:
                print("✅ Response submitted successfully!")
                # Optionally, provide the next steps or close the escalation
                self._close_escalation(escalation_id)
            else:
                print("❌ Failed to submit response. Please try again.")
                
            break  # Exit the loop after handling response
            
    def _close_escalation(self, escalation_id: str):
        """Close an escalation after human intervention."""
        print(f"🔒 Closing escalation: {escalation_id}")
        # Here you would implement the logic to close the escalation,
        # e.g., updating the database, notifying agents, etc.
        time.sleep(1)  # Simulate some processing time
        print("✅ Escalation closed.")
        
    def _view_escalation_history(self):
        """View the history of escalated cases."""
        print("\n📚 ESCALATION HISTORY")
        print("=" * 50)
        
        history = self.human_agent.get_escalation_history()
        
        if not history:
            print("✅ No escalation history found.")
            return
        
        for record in history:
            escalation_id = record['escalation_id']
            context = record['context']
            try:
                friendly_time = datetime.fromisoformat(record['timestamp']).strftime('%d %b %Y, %I:%M:%S %p')
            except Exception:
                friendly_time = record['timestamp']
            print(f"\n🆔 ID: {escalation_id}")
            print(f"⏰ Time: {friendly_time}")
            print(f"🤖 Agent: {context.get('agent_name', 'Unknown')}")
            print(f"📈 Priority: {record.get('priority', 'N/A')}")
            print(f"❓ Question: {context.get('question', 'N/A')}")
            print(f"👤 User Input: {context.get('user_input', 'N/A')}")
            print(f"💬 Response: {record.get('response', 'N/A')}")
            print("-" * 50)
            
    def _view_statistics(self):
        """View statistics about escalated cases."""
        print("\n📊 ESCALATION STATISTICS")
        print("=" * 50)
        
        stats = self.human_agent.get_escalation_statistics()
        
        if not stats:
            print("✅ No statistics available.")
            return
        
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        print("\n" + "=" * 50)
        print("Tip: Use these statistics to identify common issues and improve response strategies.")
        
    def _exit_dashboard(self):
        """Exit the dashboard."""
        print("🚪 Exiting the dashboard. Thank you for your service!")
        self.running = False
        time.sleep(1)
        
# The following code is for testing and demonstration purposes.
# In a real application, the dashboard would be launched by the agentic AI framework.

if __name__ == "__main__":
    dashboard = HumanOperatorDashboard()
    dashboard.run()
