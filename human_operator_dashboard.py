
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
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                self._view_active_escalations()
            elif choice == "2":
                self._respond_to_escalation()
            elif choice == "3":
                self._view_escalation_history()
            elif choice == "4":
                self._view_statistics()
            elif choice == "5":
                self._exit_dashboard()
            else:
                print("❌ Invalid choice. Please enter 1-5.")
                
    def _show_main_menu(self):
        """Display the main menu."""
        print("\n📋 MAIN MENU")
        print("-" * 30)
        print("1. 👀 View Active Escalations")
        print("2. 💬 Respond to Escalation")
        print("3. 📚 View Escalation History")
        print("4. 📊 View Statistics")
        print("5. 🚪 Exit Dashboard")
        
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
            print(f"\n🆔 ID: {escalation_id}")
            print(f"⏰ Time: {escalation['timestamp']}")
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
            response = input("\n✏️ Enter your response (or 'cancel' to abort): ").strip()
            
            if response.lower() == 'cancel':
                print("❌ Response cancelled.")
                return
                
            if len(response) < 10:
                print("⚠️ Response too short. Please provide a more detailed response.")
                continue
                
            # Confirm response
            print(f"\n📝 Your response: {response}")
            confirm = input("✅ Send this response? (yes/no): ").strip().lower()
            
            if confirm in ['yes', 'y']:
                success = self.human_agent.provide_human_response(escalation_id, response)
                if success:
                    print(f"✅ Response sent successfully for escalation {escalation_id}")
                    print("🔔 The user will receive your response immediately.")
                else:
                    print(f"❌ Failed to send response for escalation {escalation_id}")
                break
            elif confirm in ['no', 'n']:
                print("📝 Please enter a new response.")
                continue
            else:
                print("⚠️ Please enter 'yes' or 'no'.")
                
    def _view_escalation_history(self):
        """View all escalation history."""
        print("\n📚 ESCALATION HISTORY")
        print("=" * 50)
        
        history = self.human_agent.get_escalation_history()
        
        if not history:
            print("✅ No escalation history available.")
            return
            
        for escalation_id, escalation in sorted(history.items(), 
                                               key=lambda x: x[1]['timestamp'], 
                                               reverse=True):
            context = escalation['context']
            print(f"\n🆔 ID: {escalation_id}")
            print(f"⏰ Time: {escalation['timestamp']}")
            print(f"📊 Status: {escalation['status']}")
            print(f"🤖 Agent: {context.get('agent_name', 'Unknown')}")
            print(f"❓ Question: {context.get('question', 'N/A')[:50]}...")
            
            if escalation['status'] == 'resolved':
                print(f"✅ Response: {escalation.get('human_response', 'N/A')[:50]}...")
            elif escalation['status'] == 'timeout':
                print("⏰ Status: Timeout")
                
            print("-" * 30)
            
    def _view_statistics(self):
        """View escalation statistics."""
        print("\n📊 ESCALATION STATISTICS")
        print("=" * 50)
        
        stats = self.escalation_manager.get_failure_statistics()
        
        print(f"📈 Total Sessions: {stats['total_sessions']}")
        print(f"❌ Total Failures: {stats['total_failures']}")
        print(f"✅ Total Successes: {stats['total_successes']}")
        print(f"📊 Escalation Rate: {stats['escalation_rate']:.2%}")
        
        print(f"\n🤖 AGENT PERFORMANCE:")
        print("-" * 30)
        for agent_name, agent_stats in stats['agent_statistics'].items():
            total = agent_stats['failures'] + agent_stats['successes']
            failure_rate = agent_stats['failures'] / total if total > 0 else 0
            print(f"{agent_name}:")
            print(f"  ❌ Failures: {agent_stats['failures']}")
            print(f"  ✅ Successes: {agent_stats['successes']}")
            print(f"  📊 Failure Rate: {failure_rate:.2%}")
            
    def _exit_dashboard(self):
        """Exit the dashboard."""
        print("\n👋 Thank you for using the Human Operator Dashboard!")
        print("🔔 Remember to check back regularly for new escalations.")
        self.running = False

def main():
    """Main function to run the dashboard."""
    try:
        dashboard = HumanOperatorDashboard()
        dashboard.run()
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard closed by operator.")
    except Exception as e:
        print(f"\n❌ Dashboard error: {e}")

if __name__ == "__main__":
    main()
