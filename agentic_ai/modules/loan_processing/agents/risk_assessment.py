import json
import re
from agentic_ai.core.agent.base_agent import BaseAgent
from agentic_ai.core.utils.parsing import extract_json_from_string
from agentic_ai.core.utils.formatting import format_indian_commas

class RiskAssessmentAgent(BaseAgent):
    """Specialized agent for risk assessment."""

    def assess_risk(self, query: str) -> str:
        """Performs comprehensive risk assessment using LLM analysis."""
        try:
            # --- Risk Tiers Definition ---
            risk_tiers = [
                {
                    "name": "Low Risk",
                    "credit_score_range": [750, 900],
                    "composite_score_min": 85,
                    "decision": "approve",
                    "interest_adjustment": 0.0,
                    "notes": "Eligible for best rate and full approval"
                },
                {
                    "name": "Moderate Risk",
                    "credit_score_range": [700, 749],
                    "composite_score_min": 70,
                    "decision": "approve",
                    "interest_adjustment": 1.5,
                    "notes": "Minor premium on interest rate"
                },
                {
                    "name": "Cautionary",
                    "credit_score_range": [650, 699],
                    "composite_score_min": 60,
                    "decision": "approve_with_conditions",
                    "interest_adjustment": 2.5,
                    "max_loan_amount_pct": 80,
                    "notes": "Approval with reduced amount or shorter tenure"
                },
                {
                    "name": "High Risk",
                    "credit_score_range": [600, 649],
                    "composite_score_min": 50,
                    "decision": "escalate",
                    "require_collateral": True,
                    "collateral_type": ["property", "fixed_deposit", "co_applicant"],
                    "notes": "Escalate to human underwriter or offer secured loan"
                },
                {
                    "name": "Unacceptable",
                    "credit_score_range": [0, 599],
                    "composite_score_min": 0,
                    "decision": "reject",
                    "require_collateral": False,
                    "notes": "Reject as per lending policy"
                }
            ]
            
            print(f"⚠️ Risk assessment query: {query}")
            
            # Try to extract loan amount from the query string
            loan_amount = None
            loan_amount_pattern = re.search(r'(\d[\d,]*\.?\d*)', query)
            if loan_amount_pattern:
                try:
                    loan_amount = float(loan_amount_pattern.group(1).replace(',', ''))
                    print(f"⚠️ Extracted loan amount: {loan_amount}")
                except ValueError:
                    pass
            
            # FORCE EXTRACT credit score - most critical step
            api_credit_score = None
            # Enhanced regex pattern that's more tolerant of JSON formatting issues
            api_credit_match = re.search(r'api_credit_score"?\s*:?\s*(\d+)', query)
            if api_credit_match:
                api_credit_score = int(api_credit_match.group(1))
                print(f"⚠️ FOUND api_credit_score in query: {api_credit_score}")
            else:
                print("⚠️ WARNING: No api_credit_score found in query")
            
            if '|' not in query:
                if loan_amount:
                    # If we can extract a loan amount but no proper format,
                    # try to see if there's JSON in the query
                    user_data = extract_json_from_string(query)
                    if user_data:
                        print(f"⚠️ Extracted user data from query: {user_data}")
                    else:
                        return json.dumps({"error": "Format: user_data_json|loan_amount", "extracted_amount": loan_amount})
                else:
                    return json.dumps({"error": "Format: user_data_json|loan_amount"})
            else:
                parts = query.split('|', 1)
                user_data_str = parts[0].strip()
                loan_amount_str = parts[1].strip()
                
                if loan_amount is None:
                    try:
                        loan_amount = float(loan_amount_str)
                    except ValueError:
                        return json.dumps({"error": f"Invalid loan amount: {loan_amount_str}"})
                
                try:
                    user_data = json.loads(user_data_str)
                except json.JSONDecodeError as e:
                    # Try to extract JSON from the string
                    user_data = extract_json_from_string(user_data_str)
                    if not user_data:
                        # If that fails, try a more aggressive approach with regex
                        import re
                        pattern = r'\{[^}]*\}'
                        matches = re.findall(pattern, user_data_str)
                        if matches:
                            for potential_json in matches:
                                try:
                                    user_data = json.loads(potential_json)
                                    break
                                except:
                                    continue
                        
                        if not user_data:
                            return json.dumps({"error": f"Invalid JSON in user data: {str(e)}"})
            
            try:
                loan_amount = float(loan_amount_str)
            except ValueError:
                return json.dumps({"error": f"Invalid loan amount: {loan_amount_str}"})

            # --- Patch: Ensure credit_score is set to api_credit_score if present ---
            if isinstance(user_data, dict):
                # Use the extracted api_credit_score from regex if it exists and not in user_data
                if api_credit_score is not None and 'api_credit_score' not in user_data:
                    user_data['api_credit_score'] = api_credit_score
                
                if 'api_credit_score' in user_data:
                    user_data['credit_score'] = user_data['api_credit_score']
                    # Also patch nested user_data if present
                    if 'user_data' in user_data and isinstance(user_data['user_data'], dict):
                        user_data['user_data']['credit_score'] = user_data['api_credit_score']
            
            actual_user_data = user_data.get('user_data', user_data)
            monthly_salary = actual_user_data.get('monthly_salary', 0)
            existing_emi = actual_user_data.get('existing_emi', 0)
            
            # EMERGENCY FIX: Force correct credit score by any means necessary
            credit_score = 0
            
            # First priority: Use the regex-extracted credit score if available
            if api_credit_score is not None:
                print("⚠️ USING regex-extracted api_credit_score")
                credit_score = api_credit_score
            # Second priority: Check various places in the data structure
            elif 'api_credit_score' in user_data:
                credit_score = user_data['api_credit_score']
                print(f"⚠️ USING api_credit_score from user_data: {credit_score}")
            elif 'api_credit_score' in actual_user_data:
                credit_score = actual_user_data['api_credit_score']
                print(f"⚠️ USING api_credit_score from actual_user_data: {credit_score}")
            # Last resort: Try to directly parse the query again with a more aggressive approach
            else:
                # Super aggressive pattern that will match any number following "api_credit_score" or "credit_score" 
                last_resort_match = re.search(r'(?:api_credit_score|credit_score)[":]?\s*(\d+)', query)
                if last_resort_match:
                    credit_score = int(last_resort_match.group(1))
                    print(f"⚠️ EMERGENCY EXTRACTION: Found credit score {credit_score} in query")
                else:
                    credit_score = actual_user_data.get('credit_score', 0)
                    print(f"⚠️ NO CREDIT SCORE FOUND, defaulting to: {credit_score}")
                
            composite_score = actual_user_data.get('composite_score', None)

            # Print a visual separator to highlight risk assessment
            print("\n" + "=" * 50)
            print("🔎 RISK ASSESSMENT ANALYSIS")
            
            # Add SAFETY CHECK to prevent credit score of 0 when we know it shouldn't be
            if credit_score == 0 and api_credit_score is not None:
                print("⚠️ EMERGENCY OVERRIDE: Fixing credit score to match extracted value")
                credit_score = api_credit_score
                
            print(f"💰 Monthly Income: {format_indian_commas(monthly_salary)} | 💳 Credit Score: {credit_score} | 📊 Existing EMI: {format_indian_commas(existing_emi)}")
            print(f"💭 Thought: Analyzing financial capacity for a loan request of {format_indian_commas(loan_amount)}...")

            prompt = f"""
Analyze the loan risk for the following applicant in 3-4 concise lines.
Applicant Details:
- Monthly Salary: {format_indian_commas(monthly_salary)}
- Existing EMI: {format_indian_commas(existing_emi)}
- Credit Score: {credit_score}
Loan Requested: {format_indian_commas(loan_amount)}

Based on this information, provide a risk assessment, overall decision (Approve/Conditional/Reject), and a brief justification.
"""
            
            llm_analysis = self.llm._call(prompt)
            
            # Print the detailed thought process
            print(f"💭 Risk Analysis: {llm_analysis}")
            
            # Calculate and print debt-to-income ratio as part of thought process
            if monthly_salary > 0:
                new_emi_estimate = loan_amount / 36  # Simple estimate for a 3-year loan
                total_emi = existing_emi + new_emi_estimate
                dti_ratio = (total_emi / monthly_salary) * 100
                print(f"💭 Debt-to-Income Analysis: Current DTI: {(existing_emi/monthly_salary)*100:.1f}%, Projected DTI: {dti_ratio:.1f}%")
                if dti_ratio > 50:
                    print("💭 Warning: Projected DTI exceeds 50% safe threshold")
                elif dti_ratio > 30:
                    print("💭 Note: Projected DTI exceeds 30% recommended threshold")
            
            # --- Risk Category Calculation ---
            def get_risk_category(credit_score, composite_score=None):
                for tier in risk_tiers:
                    cs_min, cs_max = tier["credit_score_range"]
                    comp_min = tier["composite_score_min"]
                    if composite_score is not None:
                        if cs_min <= credit_score <= cs_max and composite_score >= comp_min:
                            return tier
                    else:
                        if cs_min <= credit_score <= cs_max:
                            return tier
                return risk_tiers[-1]  # Default to Unacceptable
            risk_tier = get_risk_category(credit_score, composite_score)

            print("=" * 50 + "\n")
            
            response = {
                "loan_amount_requested": loan_amount,
                "user_data_summary": {
                    "monthly_salary": monthly_salary,
                    "credit_score": credit_score,
                },
                "llm_risk_assessment": llm_analysis,
                "risk_category": risk_tier,
                "status": "dynamic_risk_assessment_completed"
            }
            
            # Final debug verification that credit score is correct
            print(f"⚠️ Final credit score used in assessment: {credit_score}")
            if api_credit_score is not None:
                print(f"⚠️ Original api_credit_score: {api_credit_score}")
                
            return json.dumps(response, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Risk assessment error: {str(e)}"})

    def run(self, query: str) -> str:
        """Runs the agent's specific task."""
        return self.assess_risk(query)

    def _format_currency(self, amount):
        return format_indian_commas(amount)
