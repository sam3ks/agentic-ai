import json
import re
from agentic_ai.core.agent.base_agent import BaseAgent
from agentic_ai.core.utils.parsing import extract_json_from_string

class RiskAssessmentAgent(BaseAgent):
    """Specialized agent for risk assessment."""

    def assess_risk(self, query: str) -> str:
        """Performs comprehensive risk assessment using LLM analysis."""
        try:
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
                        return json.dumps({"error": f"Invalid JSON in user data: {str(e)}"})
            
            try:
                loan_amount = float(loan_amount_str)
            except ValueError:
                return json.dumps({"error": f"Invalid loan amount: {loan_amount_str}"})

            actual_user_data = user_data.get('user_data', user_data)
            monthly_salary = actual_user_data.get('monthly_salary', 0)
            existing_emi = actual_user_data.get('existing_emi', 0)
            credit_score = actual_user_data.get('credit_score', 0)

            # Print a visual separator to highlight risk assessment
            print("\n" + "=" * 50)
            print("🔎 RISK ASSESSMENT ANALYSIS")
            print(f"💰 Monthly Income: ₹{monthly_salary:,.0f} | 💳 Credit Score: {credit_score} | 📊 Existing EMI: ₹{existing_emi:,.0f}")
            print(f"💭 Thought: Analyzing financial capacity for a loan request of ₹{loan_amount:,.0f}...")

            prompt = f"""
Analyze the loan risk for the following applicant in 3-4 concise lines.
Applicant Details:
- Monthly Salary: ₹{monthly_salary:,.0f}
- Existing EMI: ₹{existing_emi:,.0f}
- Credit Score: {credit_score}
Loan Requested: ₹{loan_amount:,.0f}

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
            
            print("=" * 50 + "\n")
            
            return json.dumps({
                "loan_amount_requested": loan_amount,
                "user_data_summary": {
                    "monthly_salary": monthly_salary,
                    "credit_score": credit_score,
                },
                "llm_risk_assessment": llm_analysis,
                "status": "dynamic_risk_assessment_completed"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Risk assessment error: {str(e)}"})

    def run(self, query: str) -> str:
        """Runs the agent's specific task."""
        return self.assess_risk(query)
