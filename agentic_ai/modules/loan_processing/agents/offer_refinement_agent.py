import json

class OfferRefinementAgent:
    """
    An intelligent agent that analyzes a customer's risk and financial profile
    to suggest relevant and responsible upsell/cross-sell offers.
    """

    def suggest_offers(self, risk_assessment_json: str) -> str:
        """
        Parses the risk assessment output, analyzes customer financials, and suggests offers.

        Args:
            risk_assessment_json (str): The JSON output from the RiskAssessmentAgent.

        Returns:
            str: A JSON string containing suggested offers and the reasoning behind them.
        """
        try:
            data = json.loads(risk_assessment_json)
        except json.JSONDecodeError:
            return self._create_error_response("Invalid JSON format from risk assessment.")

        # --- 1. Extract Key Financial Data ---
        risk_tier_info = data.get('risk_category', {})
        user_summary = data.get('user_data_summary', {})

        risk_category = risk_tier_info.get('name', 'Unknown').lower()
        credit_score = user_summary.get('credit_score', 0)
        monthly_income = user_summary.get('monthly_salary', 0)
        existing_emi = user_summary.get('existing_emi', 0)

        # --- 2. Calculate Financial Health Ratios ---
        if monthly_income > 0:
            disposable_income = monthly_income - existing_emi
            dti_ratio = (existing_emi / monthly_income) * 100
        else:
            disposable_income = 0
            dti_ratio = 100 # Assume highest risk if no income data

        # --- 3. Rule-Based Offer Generation Engine ---
        upsell_offer = None
        cross_sell_offer = None
        reasoning = ""

        if risk_category == 'low risk':
            if dti_ratio < 25 and disposable_income > 50000:
                upsell_offer = {
                    "name": "Premium Pre-Approved Loan",
                    "description": "Get a top-up on your loan at our best interest rates, available instantly."
                }
                cross_sell_offer = {
                    "name": "Wealth Management Services",
                    "description": "Explore personalized investment options to grow your savings."
                }
                reasoning = f"Your excellent credit score of {credit_score} and low Debt-to-Income ratio of {dti_ratio:.1f}% qualify you for our premium financial products."
            else:
                upsell_offer = {
                    "name": "High-Limit Platinum Credit Card",
                    "description": "Enjoy premium benefits, rewards, and a higher credit limit with our Platinum card."
                }
                cross_sell_offer = {
                    "name": "Comprehensive Insurance Bundle",
                    "description": "Secure your future with a bundled plan including life, health, and loan protection."
                }
                reasoning = f"With a strong credit score of {credit_score}, you are eligible for premium offers designed to provide more value and security."

        elif risk_category == 'moderate risk':
            upsell_offer = {
                "name": "Standard Credit Card",
                "description": "Build your credit history and manage expenses with our Standard credit card, featuring a competitive interest rate."
            }
            cross_sell_offer = {
                "name": "Loan Protection Insurance",
                "description": "Ensure your loan payments are covered in case of unforeseen events with our credit protection plan."
            }
            reasoning = "Based on your balanced financial profile, we recommend products that offer convenience and security."

        elif risk_category == 'cautionary':
            upsell_offer = None # Avoid suggesting more debt for cautionary profiles
            cross_sell_offer = {
                "name": "Credit Score Improvement Plan",
                "description": "Let us help you improve your credit score with our expert guidance and tools, unlocking better offers in the future."
            }
            reasoning = "To help strengthen your financial standing, we recommend focusing on services that can improve your credit health for future benefits."

        elif risk_category in ['high risk', 'unacceptable']:
            upsell_offer = None
            cross_sell_offer = {
                "name": "Financial Counseling Services",
                "description": "Connect with a financial advisor for a free session to help you manage your finances and plan for a more secure future."
            }
            reasoning = "We are committed to your financial well-being and would like to offer resources to help you strengthen your financial health."
            
        else: # Fallback for unknown risk categories
            reasoning = "Unable to generate specific offers at this time due to an unclassified risk profile."


        # --- 4. Assemble the Final Response ---
        result = {
            "customer_financial_snapshot": {
                "risk_category": risk_category.replace(" ", "_").upper(),
                "credit_score": credit_score,
                "disposable_income": f"{disposable_income:,.0f}",
                "dti_ratio_percentage": f"{dti_ratio:.1f}"
            },
            "upsell_offer": upsell_offer,
            "cross_sell_offer": cross_sell_offer,
            "reasoning": reasoning
        }
        return json.dumps(result, indent=2)

    def _create_error_response(self, error_message: str) -> str:
        """Creates a standardized JSON error response."""
        return json.dumps({
            "error": error_message,
            "upsell_offer": None,
            "cross_sell_offer": None,
            "reasoning": "An error occurred while processing the financial data for offer generation."
        }, indent=2)
        
    def run(self, query: str) -> str:
        """
        Entry point for the agent to be called by the orchestrator.
        """
        print("\n" + "="*50)
        print("💡 OFFER REFINEMENT ANALYSIS")
        print(f"💭 Analyzing risk profile to identify upsell/cross-sell opportunities...")
        
        response = self.suggest_offers(query)
        
        # Pretty print the result for the console
        try:
            response_obj = json.loads(response)
            if response_obj.get('upsell_offer') or response_obj.get('cross_sell_offer'):
                 print(f"💭 Conclusion: Found suitable offers based on financial profile.")
            else:
                 print(f"💭 Conclusion: No suitable offers recommended at this time.")
        except:
            pass # Fail silently if response is not valid json

        print("="*50 + "\n")
        return response