#!/usr/bin/env python3
"""
Test script for the enhanced sentence-transformers implementation in parsing.py
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from agentic_ai.core.utils.parsing import parse_initial_user_request

def test_enhanced_parsing():
    """Test the enhanced parsing with various input statements"""
    
    test_cases = [
        # Clear loan purposes
        "I need a loan for my education expenses",
        "Looking for a home loan to buy a house in Mumbai",
        "Need funding for car purchase, around 5 lakhs",
        "I want to take a loan for my wedding ceremony",
        "Business expansion loan needed for my startup",
        "Medical emergency loan for hospital bills",
        "Planning a vacation and need travel loan",
        
        # Ambiguous statements
        "I need money for some personal expenses",
        "Looking for financial help for investment purposes",
        "Need funds for important work",
        "I want to borrow money for my project",
        
        # Challenging cases
        "I need a loan to buy a luxury car worth 15 lakhs in Delhi",
        "Looking for education loan for my daughter's MBA program",
        "Need emergency funds for medical treatment of my father",
        "Want to invest in crypto trading with borrowed money",
        
        # Non-loan requests
        "Hello, how are you doing today?",
        "What services do you provide?",
        "Can you help me with something?",
        
        # Edge cases
        "I need a loan for something illegal",
        "Looking for money to start gambling business",
        "Need funds for stock market speculation"
    ]
    
    print("Testing Enhanced Sentence-Transformers Implementation")
    print("=" * 60)
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Input: {test_input}")
        
        try:
            result = parse_initial_user_request(test_input)
            print(f"Purpose: {result['purpose']}")
            print(f"Amount: {result['amount']}")
            print(f"City: {result['city']}")
        except Exception as e:
            print(f"Error: {str(e)}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_enhanced_parsing()
