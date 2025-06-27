#!/usr/bin/env python3
"""
Final validation test for the enhanced sentence-transformers implementation
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from agentic_ai.core.utils.parsing import parse_initial_user_request

def test_realistic_cases():
    """Test with realistic loan application scenarios"""
    
    test_cases = [
        # Real-world examples
        "I need a home loan to buy a 3BHK apartment in Mumbai worth 50 lakhs",
        "Looking for education loan for my son's engineering degree",
        "Need a car loan for purchasing a new Honda City worth 12 lakhs",
        "Emergency medical loan required for my mother's surgery",
        "Business loan needed to expand my restaurant in Bangalore",
        "Wedding loan for my daughter's marriage ceremony",
        "Travel loan for family vacation to Europe",
        "Personal loan for debt consolidation of existing loans",
        "Loan for buying gold jewelry worth 8 lakhs",
        
        # Edge cases that should be handled well
        "Can I get funding for cryptocurrency investment?",
        "Need money for gambling activities",
        "Looking for loan for stock market trading",
        "General purpose personal loan needed",
        "I want to take a loan but not sure what for",
        
        # Ambiguous cases
        "Help me with financial assistance",
        "I need money urgently",
        "Looking for some funding",
    ]
    
    print("Testing Realistic Loan Application Scenarios")
    print("=" * 60)
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Input: {test_input}")
        
        try:
            result = parse_initial_user_request(test_input)
            purpose = result['purpose']
            amount = result['amount']
            city = result['city']
            
            print(f"✓ Purpose: {purpose}")
            print(f"✓ Amount: {amount}")
            print(f"✓ City: {city}")
            
            # Check if purpose is reasonable
            if purpose != "unknown":
                success_count += 1
                print("✓ PASS")
            else:
                print("⚠ MARGINAL (purpose not detected)")
                
        except Exception as e:
            print(f"✗ FAIL: {str(e)}")
        
        print("-" * 40)
    
    print(f"\n=== SUMMARY ===")
    print(f"Successful purpose detection: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

if __name__ == "__main__":
    test_realistic_cases()
