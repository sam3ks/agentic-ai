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
import os
from typing import Dict, Any, Optional, List
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
    
    def _load_loan_purpose_policy(self) -> Dict[str, Any]:
        """Load loan purpose policy from JSON file."""
        try:
            # Get the path to the loan purpose policy file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            policy_file_path = os.path.join(current_dir, '..', 'data', 'loan_purpose_policy.json')
            
            with open(policy_file_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading loan purpose policy: {e}")
            return {}
    
    def _calculate_dynamic_tenure(self, loan_amount: float, purpose: str, credit_score: int, user_details: Dict[str, Any]) -> int:
        """
        Calculate dynamic loan tenure based on amount, purpose, and credit score.
        
        Args:
            loan_amount: Loan amount requested
            purpose: Loan purpose
            credit_score: User's credit score
            user_details: Additional user details
            
        Returns:
            Optimal tenure in months
        """
        try:
            # Load loan purpose policy
            policy = self._load_loan_purpose_policy()
            
            # Base tenure options (in months)
            tenure_options = [12, 24, 36, 48, 60]
            
            # Default tenure
            optimal_tenure = 36  # 3 years default
            
            # 1. Determine loan category and base tenure limits
            loan_category = self._classify_loan_type(purpose, policy)
            max_tenure_by_category = self._get_max_tenure_by_category(loan_category, loan_amount)
            
            # 2. Adjust based on credit score
            credit_tenure_adjustment = self._get_tenure_by_credit_score(credit_score)
            
            # 3. Adjust based on loan amount
            amount_tenure_adjustment = self._get_tenure_by_amount(loan_amount)
            
            # 4. Calculate optimal tenure starting from a reasonable base
            base_tenure = 36  # Start with 3 years as base
            adjusted_tenure = base_tenure + credit_tenure_adjustment + amount_tenure_adjustment
            
            # 5. Find closest valid tenure option
            optimal_tenure = min(tenure_options, key=lambda x: abs(x - adjusted_tenure))
            
            # 6. Ensure it doesn't exceed category maximum and is within reasonable bounds
            optimal_tenure = min(optimal_tenure, max_tenure_by_category, 60)  # Cap at 60 months max
            
            logger.info(f"Dynamic tenure calculation: amount={loan_amount}, purpose={purpose}, "
                       f"credit_score={credit_score}, category={loan_category}, "
                       f"optimal_tenure={optimal_tenure} months")
            
            return optimal_tenure
            
        except Exception as e:
            logger.error(f"Error calculating dynamic tenure: {e}")
            return 36  # Safe default of 3 years
    
    def _classify_loan_type(self, purpose: str, policy: Dict[str, Any]) -> str:
        """Classify loan type based on purpose."""
        purpose_lower = purpose.lower()
        
        # Direct match first
        if purpose_lower in policy:
            return policy[purpose_lower].get('category', 'general_personal_loan')
        
        # Fuzzy matching for common terms
        category_mapping = {
            'education': 'priority_sector',
            'home': 'retail_home_loan', 
            'house': 'retail_home_loan',
            'property': 'retail_home_loan',
            'vehicle': 'retail_vehicle_loan',
            'car': 'retail_vehicle_loan',
            'bike': 'retail_vehicle_loan',
            'business': 'MSME',
            'medical': 'personal_emergency',
            'health': 'personal_emergency',
            'wedding': 'personal_celebration',
            'marriage': 'personal_celebration',
            'travel': 'personal_lifestyle'
        }
        
        for key, category in category_mapping.items():
            if key in purpose_lower:
                return category
        
        return 'general_personal_loan'
    
    def _get_max_tenure_by_category(self, loan_category: str, loan_amount: float) -> int:
        """Get maximum tenure allowed by loan category."""
        category_limits = {
            'priority_sector': 84,      # Education: up to 7 years
            'retail_home_loan': 240,    # Home: up to 20 years
            'retail_vehicle_loan': 84,  # Vehicle: up to 7 years
            'MSME': 60,                 # Business: up to 5 years
            'personal_emergency': 48,   # Medical: up to 4 years
            'personal_celebration': 36, # Wedding: up to 3 years
            'personal_lifestyle': 24,   # Travel: up to 2 years
            'general_personal_loan': 60 # General: up to 5 years
        }
        
        max_tenure = category_limits.get(loan_category, 60)
        
        # Additional limits based on amount
        if loan_amount > 1000000:  # > 10 lakhs
            max_tenure = min(max_tenure, 84)  # Max 7 years for high amounts
        elif loan_amount > 500000:  # > 5 lakhs
            max_tenure = min(max_tenure, 60)  # Max 5 years
        elif loan_amount <= 100000:  # <= 1 lakh
            max_tenure = min(max_tenure, 36)  # Max 3 years for small amounts
        
        return max_tenure
    
    def _get_tenure_by_credit_score(self, credit_score: int) -> int:
        """Get tenure adjustment based on credit score."""
        if credit_score >= 800:    # Excellent credit
            return 12  # Allow longer tenure
        elif credit_score >= 750:  # Good credit
            return 6   # Slight extension
        elif credit_score >= 700:  # Fair credit
            return 0   # No adjustment
        elif credit_score >= 650:  # Below average
            return -6  # Shorter tenure
        else:                      # Poor credit
            return -12 # Much shorter tenure
    
    def _get_tenure_by_amount(self, loan_amount: float) -> int:
        """Get tenure adjustment based on loan amount."""
        if loan_amount >= 1000000:    # 10+ lakhs
            return 12  # Longer tenure for large amounts
        elif loan_amount >= 500000:   # 5+ lakhs
            return 6   # Moderate extension
        elif loan_amount >= 200000:   # 2+ lakhs
            return 0   # No adjustment
        elif loan_amount >= 100000:   # 1+ lakh
            return -6  # Shorter for smaller amounts
        else:                         # < 1 lakh
            return -12 # Much shorter for very small amounts
    
    def present_agreement(self, loan_details: str, selected_tenure: int = None) -> dict:
        """
        Present the loan agreement with terms and conditions, and return max tenure.
        
        Args:
            loan_details: JSON string containing loan approval details
            selected_tenure: Optional user-selected tenure (in months)
        
        Returns:
            Dict with agreement text, max tenure, and used tenure
        """
        try:
            # Parse the loan details
            if isinstance(loan_details, str):
                try:
                    details = json.loads(loan_details)
                except json.JSONDecodeError:
                    details = self._extract_details_from_text(loan_details)
            else:
                details = loan_details

            # Extract key information
            loan_amount = details.get('loan_amount', 0)
            interest_rate_raw = details.get('interest_rate', 12.0)
            user_name = details.get('user_name', 'Valued Customer')
            purpose = details.get('purpose', 'Personal Loan')
            user_details = details.get('user_details', {})
            
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
            
            # Extract credit score for dynamic tenure calculation
            credit_score = user_details.get('credit_score', 650)  # Default score
            if credit_score == 0:  # If credit score is 0, use a safe default
                credit_score = 650
            
            # Calculate max tenure
            loan_category = self._classify_loan_type(purpose, self._load_loan_purpose_policy())
            max_tenure = self._get_max_tenure_by_category(loan_category, loan_amount)

            # Calculate default or selected tenure
            if selected_tenure is not None:
                num_months = min(max(selected_tenure, 1), max_tenure)
            else:
                # For the first agreement, use the maximum available tenure
                # This ensures users see the full tenure option available to them
                num_months = max_tenure

            # Calculate EMI and other financial details
            monthly_interest_rate = interest_rate / 100 / 12
            
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
• First EMI Date: {first_emi_date.strftime('%d')}th {first_emi_date.strftime('%B %Y')}
• Final EMI Date: {final_emi_date.strftime('%d')}th {final_emi_date.strftime('%B %Y')}
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
"""
            return {
                "agreement_text": agreement_text,
                "max_tenure": max_tenure,
                "used_tenure": num_months,
                "loan_details": details  # Always return the full parsed details
            }
        except Exception as e:
            logger.error(f"Error presenting agreement: {e}")
            return {"error": f"Error presenting loan agreement: {str(e)}"}
    
    def regenerate_agreement_with_tenure(self, loan_details: str, selected_tenure: int) -> dict:
        """
        Regenerate the agreement for a user-selected tenure (in months).
        
        Args:
            loan_details: JSON string or dict with loan approval details
            selected_tenure: User-selected tenure in months
            
        Returns:
            Dict with agreement text, max tenure, and used tenure
        """
        # Accept both dict and str for loan_details
        import json
        if isinstance(loan_details, str):
            try:
                details = json.loads(loan_details)
            except Exception:
                details = self._extract_details_from_text(loan_details)
        else:
            details = loan_details
        return self.present_agreement(details, selected_tenure=selected_tenure)

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
            query_upper = query.strip().upper()
            if any(word in query_upper for word in ['I AGREE', 'I ACCEPT', 'I DECLINE', 'I REJECT', 'AGREE', 'ACCEPT', 'DECLINE', 'REJECT']):
                return self.capture_digital_acceptance(query)
            else:
                # For backward compatibility, return only agreement text
                result = self.present_agreement(query)
                return result["agreement_text"] if isinstance(result, dict) and "agreement_text" in result else str(result)
        except Exception as e:
            logger.error(f"Error in AgreementAgent.run: {e}")
            return f"Error processing agreement: {str(e)}"
