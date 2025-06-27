#!/usr/bin/env python3
"""
Quick test script for the manual loan processing workflow
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def test_manual_workflow():
    """Test the manual workflow with a realistic loan request"""
    
    from agentic_ai.modules.loan_processing.app.cli import process_loan_application
    
    # Test with a proper loan request
    test_input = "I need a home loan to buy a house in Mumbai for 25 lakhs"
    
    print("Testing Manual Workflow")
    print("=" * 60)
    print(f"Input: {test_input}")
    print("=" * 60)
    
    try:
        result = process_loan_application(test_input, automate_user=False)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_manual_workflow()
