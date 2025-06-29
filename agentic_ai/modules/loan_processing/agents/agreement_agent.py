"""
Agreement Agent

This agent is responsible for:
1. Presenting loan terms & conditions to the user
2. Capturing digital acceptance/e-signature
3. Finalizing the loan agreement process
4. Providing confirmation of agreement completion

The agent presents comprehensive loan terms based on the risk assessment
and captures the user's digital acceptance.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from agentic_ai.modules.loan_processing.agents.base_agent import BaseAgent
from agentic_ai.core.utils.formatting import format_indian_currency_without_decimal

logger = logging.getLogger(__name__)

class AgreementAgent(BaseAgent):
    """
    Agent that handles loan agreement presentation and digital acceptance.
    
    This agent takes the final loan approval details and presents them
    in a formal agreement format, then captures the user's digital signature/acceptance.
    """
    
    def __init__(self):
        super().__init__()
        self.agreement_template = self._load_agreement_template()
    
    def _load_agreement_template(self) -> Dict[str, Any]:
        """Load the standard loan agreement template."""
        return {
            "terms": {
                "loan_duration_months": 60,  # Default 5 years
                "processing_fee_percentage": 2.0,
                "prepayment_charges": "2% of outstanding amount if prepaid within 2 years",
                "late_payment_charges": "3% per month on overdue amount",
                "documentation_required": [
                    "PAN Card",
                    "Aadhaar Card", 
                    "Salary Slips (last 3 months)",
                    "Bank Statements (last 6 months)",
                    "Address Proof"
                ],
                "disbursement_timeline": "7-10 working days after agreement signing",
                "cooling_off_period": "14 days from agreement date"
            },
            "conditions": [
                "Loan amount will be disbursed to the registered bank account only",
                "EMI auto-debit mandate is mandatory",
                "Any change in employment must be notified immediately",
                "Insurance coverage is recommended but not mandatory",
                "Loan account will be reported to credit bureaus"
            ]
        }
    
    def present_agreement(self, loan_details: str) -> str:
        """
        Present the loan agreement with terms and conditions.
        
        Args:
            loan_details: JSON string containing loan approval details
            
        Returns:
            Formatted agreement for user review
        """
        try:
            # Parse the loan details
            if isinstance(loan_details, str):
                try:
                    details = json.loads(loan_details)
                except json.JSONDecodeError:
                    # If not JSON, treat as simple text and extract basic info
                    details = self._extract_details_from_text(loan_details)
            else:
                details = loan_details
            
            # Extract key information
            loan_amount = details.get('loan_amount', 0)
            interest_rate_raw = details.get('interest_rate', 12.0)
            user_name = details.get('user_name', 'Valued Customer')
            purpose = details.get('purpose', 'Personal Loan')
            
            # Handle interest rate - convert string rates to numeric values
            if isinstance(interest_rate_raw, str):
                if 'best rate' in interest_rate_raw.lower():
                    interest_rate = 10.0  # Best rate - lowest interest
                elif 'premium' in interest_rate_raw.lower():
                    interest_rate = 14.0  # Premium rate
                else:
                    # Try to extract numeric value from string
                    import re
                    rate_match = re.search(r'(\d+(?:\.\d+)?)', str(interest_rate_raw))
                    if rate_match:
                        interest_rate = float(rate_match.group(1))
                    else:
                        interest_rate = 12.0  # Default fallback
            else:
                interest_rate = float(interest_rate_raw) if interest_rate_raw else 12.0
            
            # Calculate EMI and other financial details
            monthly_interest_rate = interest_rate / 100 / 12
            num_months = self.agreement_template['terms']['loan_duration_months']
            
            if monthly_interest_rate > 0:
                emi = loan_amount * monthly_interest_rate * (1 + monthly_interest_rate)**num_months / ((1 + monthly_interest_rate)**num_months - 1)
            else:
                emi = loan_amount / num_months
            
            processing_fee = loan_amount * self.agreement_template['terms']['processing_fee_percentage'] / 100
            
            # Generate agreement date and repayment schedule
            agreement_date = datetime.now()
            first_emi_date = agreement_date + timedelta(days=30)
            final_emi_date = first_emi_date + timedelta(days=30 * (num_months - 1))
            
            # Format the agreement
            agreement_text = f"""
LOAN AGREEMENT & TERMS
====================================================================

BORROWER DETAILS:
• Name: {user_name}
• Loan Purpose: {purpose}
• Agreement Date: {agreement_date.strftime('%d-%m-%Y')}

LOAN DETAILS:
• Principal Amount: {format_indian_currency_without_decimal(int(loan_amount))}
• Interest Rate: {interest_rate}% per annum
• Loan Tenure: {num_months} months ({num_months//12} years)
• Monthly EMI: {format_indian_currency_without_decimal(int(emi))}
• Processing Fee: {format_indian_currency_without_decimal(int(processing_fee))}
• Total Amount Payable: {format_indian_currency_without_decimal(int(emi * num_months))}

REPAYMENT SCHEDULE:
• First EMI Date: {first_emi_date.strftime('%d-%m-%Y')}
• Final EMI Date: {final_emi_date.strftime('%d-%m-%Y')}
• EMI Deduction: Auto-debit from registered bank account

TERMS & CONDITIONS:
"""
            
            # Add terms and conditions
            for i, condition in enumerate(self.agreement_template['conditions'], 1):
                agreement_text += f"{i}. {condition}\n"
            
            agreement_text += f"""
CHARGES & FEES:
• Processing Fee: {self.agreement_template['terms']['processing_fee_percentage']}% of loan amount
• Late Payment Charges: {self.agreement_template['terms']['late_payment_charges']}
• Prepayment Charges: {self.agreement_template['terms']['prepayment_charges']}

DOCUMENTATION REQUIRED:
"""
            
            for doc in self.agreement_template['terms']['documentation_required']:
                agreement_text += f"• {doc}\n"
            
            agreement_text += f"""
IMPORTANT NOTES:
• Disbursement Timeline: {self.agreement_template['terms']['disbursement_timeline']}
• Cooling-off Period: {self.agreement_template['terms']['cooling_off_period']}

====================================================================

DIGITAL ACCEPTANCE REQUIRED
By proceeding with digital acceptance, you confirm that:
1. You have read and understood all terms and conditions
2. You agree to the repayment schedule and charges
3. You authorize auto-debit for EMI payments
4. You will provide all required documentation

To proceed with digital acceptance, please respond with:
"I AGREE" or "I ACCEPT" - to accept the terms
"I DECLINE" or "I REJECT" - to decline the loan

Note: This agreement is valid for 48 hours from the date of presentation.
"""
            
            return agreement_text
            
        except Exception as e:
            logger.error(f"Error presenting agreement: {e}")
            return f"Error presenting loan agreement: {str(e)}"
    
    def capture_digital_acceptance(self, user_response: str) -> str:
        """
        Capture and process the user's digital acceptance.
        
        Args:
            user_response: User's response to the agreement
            
        Returns:
            Confirmation of acceptance or rejection
        """
        try:
            response = user_response.strip().upper()
            timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
            
            # Check for acceptance
            if any(accept_word in response for accept_word in ['I AGREE', 'I ACCEPT', 'AGREE', 'ACCEPT', 'YES']):
                
                # Generate digital signature record
                signature_record = {
                    "status": "ACCEPTED",
                    "timestamp": timestamp,
                    "user_response": user_response,
                    "digital_signature": f"ESIGN_{timestamp.replace(' ', '_').replace(':', '').replace('-', '')}",
                    "ip_address": "127.0.0.1",  # In real implementation, capture actual IP
                    "agreement_version": "1.0"
                }
                
                confirmation = f"""
LOAN AGREEMENT DIGITALLY ACCEPTED
====================================================================

ACCEPTANCE CONFIRMATION:
• Status: ACCEPTED
• Digital Signature ID: {signature_record['digital_signature']}
• Acceptance Date & Time: {timestamp}
• Agreement Status: LEGALLY BINDING

NEXT STEPS:
1. Documentation Submission: Please submit all required documents within 5 working days
2. Account Setup: Ensure your bank account details are updated for EMI auto-debit
3. Verification: Our team will verify your documents and contact you within 2 working days
4. Disbursement: Loan amount will be credited to your account within 7-10 working days

IMPORTANT REMINDERS:
• Keep this confirmation for your records
• Your first EMI will be auto-debited 30 days from today
• You can track your loan status through our customer portal
• 24/7 customer support available for any queries

CONTACT INFORMATION:
• Customer Care: 1800-XXX-XXXX
• Email: support@loanbank.com
• Portal: www.loanbank.com/myaccount

Thank you for choosing our services!
Your loan application has been successfully processed and accepted.
"""
                
                return confirmation
                
            # Check for rejection
            elif any(reject_word in response for reject_word in ['I DECLINE', 'I REJECT', 'DECLINE', 'REJECT', 'NO']):
                
                rejection_record = {
                    "status": "REJECTED",
                    "timestamp": timestamp,
                    "user_response": user_response
                }
                
                confirmation = f"""
LOAN AGREEMENT DECLINED
====================================================================

REJECTION CONFIRMATION:
• Status: DECLINED
• Rejection Date & Time: {timestamp}
• Agreement Status: TERMINATED

WHAT THIS MEANS:
• Your loan application has been cancelled
• No further processing will occur
• No charges or fees will be applied
• Your credit score will not be impacted by this rejection

FUTURE APPLICATIONS:
• You can reapply for a loan at any time
• Your application data will be retained for 90 days
• Consider reviewing our terms and conditions for future reference

FEEDBACK:
We value your feedback. If you declined due to specific concerns about our terms,
please contact our customer care team at 1800-XXX-XXXX.

Thank you for considering our services.
"""
                
                return confirmation
                
            else:
                # Unclear response
                return f"""
UNCLEAR RESPONSE
====================================================================

We couldn't clearly understand your response: "{user_response}"

Please provide a clear response:
• Type "I AGREE" or "I ACCEPT" to accept the loan terms
• Type "I DECLINE" or "I REJECT" to decline the loan

Note: Your response must be clear and unambiguous for legal compliance.
The agreement remains valid for 48 hours from presentation.
"""
                
        except Exception as e:
            logger.error(f"Error capturing digital acceptance: {e}")
            return f"Error processing your response: {str(e)}"
    
    def _extract_details_from_text(self, text: str) -> Dict[str, Any]:
        """Extract loan details from text if JSON parsing fails."""
        details = {}
        
        # Try to extract loan amount
        import re
        amount_match = re.search(r'(?:amount|loan).*?(\d+(?:,\d+)*)', text, re.IGNORECASE)
        if amount_match:
            details['loan_amount'] = int(amount_match.group(1).replace(',', ''))
        
        # Try to extract interest rate
        rate_match = re.search(r'(?:rate|interest).*?(\d+(?:\.\d+)?)%?', text, re.IGNORECASE)
        if rate_match:
            details['interest_rate'] = float(rate_match.group(1))
        
        # Try to extract purpose
        purpose_match = re.search(r'(?:purpose|for).*?([a-zA-Z\s]+)', text, re.IGNORECASE)
        if purpose_match:
            details['purpose'] = purpose_match.group(1).strip()
        
        return details
    
    def run(self, query: str) -> str:
        """
        Main entry point for the Agreement Agent.
        
        Args:
            query: Either loan details for agreement presentation or user response for acceptance
            
        Returns:
            Agreement presentation or acceptance confirmation
        """
        try:
            # Check if this is a user response to an existing agreement
            query_upper = query.strip().upper()
            if any(word in query_upper for word in ['I AGREE', 'I ACCEPT', 'I DECLINE', 'I REJECT', 'AGREE', 'ACCEPT', 'DECLINE', 'REJECT']):
                return self.capture_digital_acceptance(query)
            else:
                # This is loan details for agreement presentation
                return self.present_agreement(query)
                
        except Exception as e:
            logger.error(f"Error in AgreementAgent.run: {e}")
            return f"Error processing agreement: {str(e)}"
