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
            # EMERGENCY OVERRIDE - SIMPLIFIED METHOD
            # Let's create a basic but reliable implementation that doesn't rely on regex
            
            # Step 1: Split the query to get user_data and loan_amount
            if '|' in query:
                parts = query.split('|', 1)
                user_data_str = parts[0].strip()
                loan_amount_str = parts[1].strip()
                
                # Step 2: Parse loan amount
                try:
                    loan_amount = float(loan_amount_str.replace(',', ''))
                except:
                    loan_amount = 500000  # Default to 5 lakh if parsing fails
                    
                # Step 3: Find api_credit_score in the user data string
                api_credit_score = None
                if "api_credit_score" in user_data_str:
                    # Best effort to extract credit score without regex
                    start_idx = user_data_str.find("api_credit_score") + len("api_credit_score")
                    # Find the colon
                    colon_idx = user_data_str.find(":", start_idx)
                    if colon_idx != -1:
                        # Find the first digit after colon
                        digit_idx = colon_idx + 1
                        while digit_idx < len(user_data_str) and not user_data_str[digit_idx].isdigit():
                            digit_idx += 1
                        if digit_idx < len(user_data_str):
                            # Extract the number
                            end_idx = digit_idx
                            while end_idx < len(user_data_str) and user_data_str[end_idx].isdigit():
                                end_idx += 1
                            try:
                                api_credit_score = int(user_data_str[digit_idx:end_idx])
                            except:
                                pass
                
                # Step 4: Parse user_data as json
                try:
                    user_data = json.loads(user_data_str)
                except:
                    # Create a minimal user_data if parsing fails
                    user_data = {
                        "monthly_salary": 50000,
                        "existing_emi": 0,
                        "user_id": "unknown"
                    }
            
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
            
            
            # Try to extract loan amount from the query string
            loan_amount = None
            try:
                import re
                loan_amount_pattern = re.search(r'(\d[\d,]*\.?\d*)', query)
                if loan_amount_pattern:
                    try:
                        loan_amount = float(loan_amount_pattern.group(1).replace(',', ''))
                    except ValueError:
                        pass
            except Exception as e:
                # Default to 0 if extraction fails
                loan_amount = 0
            
            # FORCE EXTRACT credit score - most critical step
            api_credit_score = None
            try:
                import re
                # Enhanced regex pattern that's more tolerant of JSON formatting issues
                api_credit_match = re.search(r'api_credit_score"?\s*:?\s*(\d+)', query)
                if api_credit_match:
                    api_credit_score = int(api_credit_match.group(1))
            except Exception as e:
                # Try again with a simpler pattern
                try:
                    import re
                    api_credit_match = re.search(r'api_credit_score.*?(\d+)', query)
                    if api_credit_match:
                        api_credit_score = int(api_credit_match.group(1))
                except Exception as e2:
                    pass
            
            if '|' not in query:
                if loan_amount:
                    # If we can extract a loan amount but no proper format,
                    # try to see if there's JSON in the query
                    user_data = extract_json_from_string(query)
                    if user_data:
                        pass  # User data extracted successfully
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
                        # Use the global re module (don't import again)
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
            
            # EMERGENCY ABSOLUTE FIX: Force correct credit score by any means necessary
            credit_score = 0
            extracted_credit_scores = []
            
            # First priority: Use the regex-extracted credit score if available
            if api_credit_score is not None:
                credit_score = api_credit_score
                extracted_credit_scores.append(("regex extraction", api_credit_score))
                
            # Second priority: Check various places in the data structure
            if 'api_credit_score' in user_data:
                user_data_score = user_data['api_credit_score']
                extracted_credit_scores.append(("user_data['api_credit_score']", user_data_score))
                if credit_score == 0:  # Only update if not already set
                    credit_score = user_data_score
                    
            if 'api_credit_score' in actual_user_data:
                actual_user_data_score = actual_user_data['api_credit_score']
                extracted_credit_scores.append(("actual_user_data['api_credit_score']", actual_user_data_score))
                if credit_score == 0:  # Only update if not already set
                    credit_score = actual_user_data_score
                    
            # Search directly in the raw query string (most aggressive approach)
            try:
                all_credit_scores = re.findall(r'(?:api_credit_score|credit_score)[":]?\s*(\d+)', query)
                for i, score_str in enumerate(all_credit_scores):
                    try:
                        score = int(score_str)
                        extracted_credit_scores.append((f"raw query match #{i+1}", score))
                        if credit_score == 0:  # Only update if not already set
                            credit_score = score
                    except ValueError:
                        pass
            except Exception as e:
                # Try a simple digit extraction if regex fails
                try:
                    import re  # Re-import to ensure availability
                    digits = re.findall(r'\d+', query)
                    for digit in digits:
                        if len(digit) == 3:  # Credit scores are typically 3 digits
                            score = int(digit)
                            if 300 <= score <= 900:  # Valid credit score range
                                extracted_credit_scores.append(("digit extraction", score))
                                if credit_score == 0:
                                    credit_score = score
                except Exception as e2:
                    pass
                    
            # If everything failed, try to get from user data directly
            if credit_score == 0:
                fallback_score = actual_user_data.get('credit_score', 0)
                extracted_credit_scores.append(("actual_user_data.get('credit_score')", fallback_score))
                credit_score = fallback_score
            
            # Remove debug arrays from final output for cleaner display
            
            # Last chance override - if we found any valid score and we're still at 0, use the highest one
            if credit_score == 0 and extracted_credit_scores:
                all_valid_scores = [score for _, score in extracted_credit_scores if score > 0]
                if all_valid_scores:
                    credit_score = max(all_valid_scores)
            
            # Force update both data structures with our final credit score value if it's > 0
            if credit_score > 0:
                user_data['credit_score'] = credit_score
                user_data['api_credit_score'] = credit_score
                if isinstance(actual_user_data, dict):
                    actual_user_data['credit_score'] = credit_score
                    actual_user_data['api_credit_score'] = credit_score
                    
            composite_score = actual_user_data.get('composite_score', None)

            # Print a visual separator to highlight risk assessment
            print("\n" + "=" * 50)
            print("🔎 RISK ASSESSMENT ANALYSIS")
            
            # Add SAFETY CHECK to prevent credit score of 0 when we know it shouldn't be
            if credit_score == 0 and api_credit_score is not None:
                credit_score = api_credit_score
                
            print(f"💰 Monthly Income: {format_indian_commas(monthly_salary)} | 💳 Credit Score: {credit_score} | 📊 Existing EMI: {format_indian_commas(existing_emi)}")
            print(f"💭 Thought: Analyzing financial capacity for a loan request of {format_indian_commas(loan_amount)}...")

            prompt = f"""
Analyze the loan risk for the following applicant in 3-4 concise lines.
Applicant Details:
- Monthly Salary: {format_indian_commas(monthly_salary)}
- Existing EMI: {format_indian_commas(existing_emi)}
- Credit Score: {credit_score}  # IMPORTANT: This credit score of {credit_score} is accurate and should be used as-is
Loan Requested: {format_indian_commas(loan_amount)}

Based on this information, provide a risk assessment, overall decision (Approve/Conditional/Reject), and a brief justification.
IMPORTANT: Preserve the exact credit score of {credit_score} in your assessment. Do not change or override this value.
"""
            
            llm_analysis = self.llm._call(prompt)
            
            # CRITICAL FIX: Remove any "Action Input:" from the LLM's response
            # This prevents the LLM from generating a new Action Input inside risk assessment
            if "Action Input:" in llm_analysis:
                llm_analysis = llm_analysis.split("Action Input:")[0].strip()
                
            # NEW FIX: Replace any incorrect credit score the LLM might have generated in its response
            # This handles cases where the LLM tries to be helpful and include a credit score in its analysis
            # but it doesn't match our actual credit score
            if credit_score > 0:
                try:
                    # Replace phrases like "credit score of 0" or "credit score: 0" with our actual score
                    llm_analysis = re.sub(r'credit score\s*(?:of|:)\s*\d+', f'credit score: {credit_score}', 
                                        llm_analysis, flags=re.IGNORECASE)
                    # Also replace standalone references like "with a 600 credit score" 
                    llm_analysis = re.sub(r'(\s|^)(\d{3})(\s+credit score)', f'\\1{credit_score}\\3', 
                                        llm_analysis, flags=re.IGNORECASE)
                except Exception as e:
                    # Just add the credit score at the beginning if regex fails
                    llm_analysis = f"[Credit Score: {credit_score}] " + llm_analysis
            
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
                # Validate credit score is non-zero
                if credit_score == 0 and extracted_credit_scores:
                    valid_scores = [score for _, score in extracted_credit_scores if score > 0]
                    if valid_scores:
                        credit_score = max(valid_scores)
                
                # Find matching tier
                for tier in risk_tiers:
                    cs_min, cs_max = tier["credit_score_range"]
                    comp_min = tier["composite_score_min"]
                    
                    # Check credit score range
                    credit_score_match = cs_min <= credit_score <= cs_max
                    
                    # Check composite score if available
                    comp_score_match = True
                    if composite_score is not None:
                        comp_score_match = composite_score >= comp_min
                    
                    if credit_score_match and comp_score_match:
                        return tier
                        
                return risk_tiers[-1]  # Default to Unacceptable
                
            risk_tier = get_risk_category(credit_score, composite_score)

            print("=" * 50 + "\n")
            
            response = {
                "loan_amount_requested": loan_amount,
                "user_data_summary": {
                    "monthly_salary": monthly_salary,
                    "credit_score": credit_score,
                    "api_credit_score": api_credit_score if api_credit_score is not None else credit_score,
                },
                "llm_risk_assessment": llm_analysis,
                "risk_category": risk_tier,
                "status": "dynamic_risk_assessment_completed"
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            # ULTRA FALLBACK MODE - This will always work even if everything else fails
            try:
                # Extract any number that could be a credit score
                credit_score = 0
                
                if "api_credit_score" in query:
                    for part in query.split():
                        if part.isdigit() and 300 <= int(part) <= 900:
                            credit_score = int(part)
                            break
                
                risk_tier = {
                    "name": "Emergency Fallback",
                    "credit_score_range": [0, 900],
                    "composite_score_min": 0, 
                    "decision": "escalate",
                    "notes": "Error occurred during assessment; manual review required"
                }
                
                if credit_score >= 750:
                    risk_tier["decision"] = "approve"
                elif credit_score >= 600:
                    risk_tier["decision"] = "approve_with_conditions"
                
                response = {
                    "loan_amount_requested": 500000,
                    "user_data_summary": {"credit_score": credit_score},
                    "llm_risk_assessment": "Error occurred during assessment. This is an emergency fallback response.",
                    "risk_category": risk_tier,
                    "status": "emergency_fallback_assessment",
                    "error": str(e)
                }
                
                return json.dumps(response, indent=2)
            except:
                # Absolute last resort
                return json.dumps({
                    "error": f"Risk assessment critical failure: {str(e)}",
                    "status": "critical_error",
                    "recommendation": "Please contact IT support."
                })

    def run(self, query: str) -> str:
        """Runs the agent's specific task."""
        return self.assess_risk(query)

    def _format_currency(self, amount):
        return format_indian_commas(amount)
