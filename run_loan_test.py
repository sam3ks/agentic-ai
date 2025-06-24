"""
Test script for the LoanPurposeAssessmentAgent.

This script demonstrates how the agent identifies loan purposes 
and checks them against policy rules.
"""

import os
import sys
import json
import logging
from pprint import pprint

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Find the project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(script_dir)

# Add project root to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added project root to sys.path: {project_root}")

print(f"Current working directory: {os.getcwd()}")
print(f"Project root: {project_root}")

try:
    # Import the agent (will work if path is set correctly)
    from agentic_ai.modules.loan_processing.agents.loan_purpose_assessment import LoanPurposeAssessmentAgent
    print("Successfully imported LoanPurposeAssessmentAgent")
    
    # Create and test the agent
    agent = LoanPurposeAssessmentAgent()
    
    # Example loan purposes to test
    test_purposes = [
        "I need money for education",
        "I want to buy a car", 
        "I need money for hospital bills and surgery",
        "Need funds for gambling",
        "Want to invest in Bitcoin and cryptocurrencies",
        "I'm planning my wedding next month"
    ]
    
    print("\n=== TEST RESULTS ===")
    for purpose in test_purposes:
        print(f"\nTesting purpose: '{purpose}'")
        result = agent.run(purpose)
        
        # Display the result
        if result.get("matched_category"):
            print(f"✓ Matched to: {result['matched_category']}")
            print(f"✓ Permitted: {result.get('is_permitted', False)}")
            
            # Show policy details in a readable format
            if result.get("policy_details"):
                details = result["policy_details"]
                print("\nPolicy Details:")
                print(f"  Category: {details.get('category')}")
                
                if details.get("eligibility") == "permitted":
                    print(f"  Requirement: {details.get('requirement', 'N/A')}")
                else:
                    print(f"  Reason: {details.get('reason', 'Not specified')}")
                    
                print(f"  Notes: {details.get('notes', 'N/A')}")
        else:
            print("✗ No clear match found")
            print(f"Message: {result.get('message', 'Unknown error')}")
            
except Exception as e:
    logger.error(f"Error running test: {e}", exc_info=True)
    print(f"\nERROR: {e}")

print("\nTest complete!")
