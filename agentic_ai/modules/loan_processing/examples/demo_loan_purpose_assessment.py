"""
Example script to demonstrate the LoanPurposeAssessmentAgent functionality.

This script provides a simple interactive interface to test the agent.
"""

import sys
import os
import json
from typing import Dict, Any
import logging

# Add the parent directory to sys.path to import modules correctly
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

from agentic_ai.modules.loan_processing.agents.loan_purpose_assessment import LoanPurposeAssessmentAgent

def format_result(result: Dict[str, Any]) -> str:
    """Format the result for display."""
    if not result.get("matched_category"):
        return f"""
🚫 NO MATCH FOUND
------------------------
Best match score: {result.get('similarity_score', 0):.2f}
Message: {result.get('message', 'Unknown error')}

Please provide a clearer description of your loan purpose.
"""
    
    policy = result.get("policy_details", {})
    
    eligibility = policy.get('eligibility', 'unknown')
    icon = "✅" if eligibility == "permitted" else "⚠️" if eligibility == "conditionally_permitted" else "❌"
    
    output = f"""
{icon} LOAN PURPOSE: {result.get('matched_category').upper()}
------------------------
Category: {policy.get('category', 'N/A')}
Eligibility: {eligibility.upper()}
"""
    
    if policy.get('requirement'):
        output += f"Requirement: {policy.get('requirement')}\n"
    
    if policy.get('reason'):
        output += f"Reason: {policy.get('reason')}\n"
    
    output += f"""
Notes: {policy.get('notes', 'N/A')}
Policy Reference: {policy.get('policy_ref', 'N/A')}

Confidence Score: {result.get('similarity_score', 0):.2f}
"""
    return output

def interactive_demo():
    """Run an interactive demo of the loan purpose assessment agent."""
    agent = LoanPurposeAssessmentAgent()
    
    print("\n" + "="*70)
    print("🏦 LOAN PURPOSE ASSESSMENT AGENT - INTERACTIVE DEMO 🏦")
    print("="*70)
    print("\nThis demo will evaluate loan purposes against policy criteria.")
    print("Enter 'quit', 'exit', or 'q' to end the demo.\n")
    
    while True:
        user_input = input("\n💬 Please describe the purpose of your loan: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nThank you for using the Loan Purpose Assessment Demo!")
            break
        
        if not user_input:
            print("Please provide a purpose for your loan.")
            continue
        
        # Process the input
        result = agent.run(user_input)
        formatted_result = format_result(result)
        print(formatted_result)

if __name__ == "__main__":
    interactive_demo()
