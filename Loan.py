'''Fixed Input validation of User city and New User Salary Sheet Generation
EXPLANATION: If user enters other city instead of Available cities, 
it will ask the user to enter the correct city available in the list.
For new users, mock salary sheet is generated and financial data is extracted.
''' 
import os
import pandas as pd
import numpy as np
import json
import re
import warnings
from typing import Any, Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Groq imports
from groq import Groq

warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()



class Loan_processing_AI_agent2:
    """Configuration and implementation for the loan processing system."""
    
    class Config:
        """Configuration management for the loan processing system."""
        
        def __init__(self):
            self.groq_api_key = self._get_groq_api_key()
            self.dataset_path = 'Loan_Dataset_V1.csv'
            self.max_loan_amount = 2000000
            self.min_credit_score = 300
            self.max_credit_score = 850
    
        def _get_groq_api_key(self) -> str:
            """Get Groq API key from environment variables."""
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                print("⚠️ GROQ_API_KEY not found. System may use fallback mode.")
                return ""
            return api_key
    
    @staticmethod
    def main():
        """Main application entry point."""
        print("=" * 60)
        print("🏦 MULTI-AGENT LOAN PROCESSING SYSTEM")
        print("=" * 60)
        
        try:
            # Initialize system
            config = Loan_processing_AI_agent2.Config()
            data_manager = Loan_processing_AI_agent2.LoanDataManager(config.dataset_path)
            processor = Loan_processing_AI_agent2.MasterLoanProcessor(data_manager, config)
            
            # Get user input
            user_request = input("\n💬 Please describe your loan requirement (e.g., 'I need a personal loan for 5 lakhs with PAN ABCDE1234F.' or 'New user, need a home loan for 70 lakhs, my estimated salary is 80000 and credit score is 720.'): ").strip()
            
            if not user_request:
                print("❌ Request cannot be empty")
                return
            
            print(f"\n{'='*60}")
            print("🔄 MULTI-AGENT PROCESSING...")
            print("=" * 60)
            
            # Process application through multi-agent system
            result = processor.process_application(user_request)
            
            print(f"\n{'='*60}")
            print("✅ PROCESSING COMPLETE")
            print("=" * 60)
            print(result)
            
        except Exception as e:
            print(f"❌ System error: {str(e)}")

    @staticmethod
    def process_single_query(user_input: str) -> str:
        """
        Process a single loan query without entering interactive mode.
        This method is used for integration with the main orchestrator.
        """
        print(f"[DEBUG] process_single_query called with: {user_input}")
        try:
            # Initialize system components with proper config
            print("[DEBUG] Initializing config...")
            config = Loan_processing_AI_agent2.Config()
            print("[DEBUG] Initializing data manager...")
            data_manager = Loan_processing_AI_agent2.LoanDataManager(config.dataset_path)
            print("[DEBUG] Initializing processor...")
            processor = Loan_processing_AI_agent2.MasterLoanProcessor(data_manager, config)
            
            # Process the application
            print("[DEBUG] Processing application...")
            result = processor.process_application(user_input)
            print(f"[DEBUG] process_single_query result: {result}")
            return result
            
        except Exception as e:
            print(f"[ERROR] process_single_query failed: {str(e)}")
            # Enhanced fallback processing
            try:
                # Extract loan amount from input
                amount_match = re.search(r'₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs)?', user_input.lower())
                if amount_match:
                    amount_value = float(amount_match.group(1))
                    loan_amount = amount_value * 100000 if 'lakh' in user_input.lower() else amount_value
                else:
                    amount_match = re.search(r'₹?\s*(\d+(?:,\d+)*)', user_input)
                    loan_amount = float(amount_match.group(1).replace(',', '')) if amount_match else 500000
                
                fallback_msg = f"""
🏦 **LOAN APPLICATION ERROR**

**Error Details:** {str(e)}
**Requested Input:** {user_input}

📋 **Application Details:**
• Requested Amount: ₹{loan_amount:,.0f}
• Application ID: LA{datetime.now().strftime('%Y%m%d%H%M%S')}
• Status: Failed

⚠️ **Next Steps:**
1. Verify GROQ_API_KEY is set
2. Check system configuration
3. Resubmit with:
   - PAN/Aadhaar
   - City
   - Loan purpose/amount
   - For new users, be prepared to provide estimated salary, existing EMI, and credit score.

📞 **Support:**
Contact our helpline for assistance.
                """
                return fallback_msg
                
            except Exception as fallback_e:
                return f"Loan application failed. Error: {str(fallback_e)}. Please contact support."
    
    @staticmethod
    def get_agent_status() -> Dict[str, Any]:
        """Get the current status of the loan processing agent."""
        try:
            config = Loan_processing_AI_agent2.Config()
            return {
                "agent_type": "Loan_Processing",
                "max_loan_amount": config.max_loan_amount,
                "dataset_path": config.dataset_path,
                "groq_api_available": bool(config.groq_api_key),
                "status": "operational"
            }
        except Exception as e:
            return {
                "agent_type": "Loan_Processing",
                "status": "error",
                "error": str(e)
            }

if __name__ == "__main__":
    Loan_processing_AI_agent2.main()