from agentic_ai.modules.loan_processing.agents.agreement_agent import AgreementAgent

agent = AgreementAgent()

# Test different scenarios
test_cases = [
    {'amount': 100000, 'purpose': 'education', 'credit_score': 750},
    {'amount': 500000, 'purpose': 'home purchase', 'credit_score': 700},
    {'amount': 200000, 'purpose': 'vehicle purchase', 'credit_score': 650}
]

print('Dynamic Tenure Verification:')
for i, case in enumerate(test_cases, 1):
    user_details = {'credit_score': case['credit_score']}
    tenure = agent._calculate_dynamic_tenure(case['amount'], case['purpose'], case['credit_score'], user_details)
    print(f'{i}. Amount: ₹{case["amount"]:,} | Purpose: {case["purpose"]} | Credit: {case["credit_score"]} | Tenure: {tenure} months')
