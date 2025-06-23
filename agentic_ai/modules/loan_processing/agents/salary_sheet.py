import json
import re
from agentic_ai.core.agent.base_agent import BaseAgent

class SalarySheetGeneratorAgent(BaseAgent):
    """Agent to generate mock salary sheet data for new users."""

    def generate_mock_salary_sheet(self, query: str) -> str:
        """Generates mock salary sheet data based on user hints."""
        print(f"📋 Generating mock salary sheet for new user...")
        print(f"[DEBUG] SalarySheetGenerator received query: {query}")
        try:
            hints = {}
            for part in query.split(','):
                if ':' in part:
                    key, value = part.split(':', 1)
                    hints[key.strip()] = value.strip()

            identifier = hints.get("user_identifier", "N/A")
            salary_hint = float(hints.get("salary_hint", 0))
            emi_hint = float(hints.get("emi_hint", 0))
            credit_hint = int(hints.get("credit_hint", 0))

            pan_pattern = r'^[A-Z]{5}\d{4}[A-Z]$'
            aadhaar_pattern = r'^\d{12}$'
            
            prompt_lines = [
                "Generate a mock salary sheet details for a new user with the following hints.",
                "Provide realistic values. Ensure Credit Score is between 300-850.",
                "",
                f"User Identifier: {identifier}",
                f"Monthly Salary Hint: ₹{salary_hint:,.0f}",
                f"Existing EMI Hint: ₹{emi_hint:,.0f}",
                f"Credit Score Hint: {credit_hint}",
                "",
                "Respond in JSON format with generated data:",
                "{",
                f'    "pan_number": "{identifier if re.match(pan_pattern, identifier) else "N/A"}",',
                f'    "aadhaar_number": "{identifier if re.match(aadhaar_pattern, identifier) else "N/A"}",',
                '    "monthly_salary": numeric_salary,',
                '    "existing_emi": numeric_emi,',
                '    "credit_score": numeric_credit_score,',
                '    "delayed_payments": numeric_delayed_payments,',
                '    "avg_monthly_balance": numeric_avg_monthly_balance,',
                '    "avg_daily_transactions": numeric_avg_daily_transactions,',
                '    "source": "mock_salary_sheet_generated"',
                "}"
            ]
            
            prompt = "\n".join(prompt_lines)
            llm_response = self.llm._call(prompt)
            
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                mock_data = json.loads(json_match.group(0))
            else:
                raise ValueError("Could not parse JSON from LLM response for salary sheet generation.")

            mock_data['monthly_salary'] = max(15000.0, float(mock_data.get('monthly_salary', salary_hint or 50000)))
            mock_data['existing_emi'] = max(0.0, float(mock_data.get('existing_emi', emi_hint or (mock_data['monthly_salary'] * 0.1))))
            mock_data['credit_score'] = min(850, max(300, int(mock_data.get('credit_score', credit_hint or 650))))
            mock_data['delayed_payments'] = max(0, int(mock_data.get('delayed_payments', 0)))
            mock_data['avg_monthly_balance'] = max(0.0, float(mock_data.get('avg_monthly_balance', mock_data['monthly_salary'] * 0.4)))
            mock_data['avg_daily_transactions'] = max(0, int(mock_data.get('avg_daily_transactions', 5)))

            print(f"✅ Mock salary sheet generated successfully!")
            return json.dumps(mock_data, indent=2)

        except Exception as e:
            print(f"[ERROR] SalarySheetGenerator error: {str(e)}")
            return json.dumps({"error": f"Failed to generate mock salary sheet: {str(e)}"})

    def run(self, query: str) -> str:
        """Runs the agent's specific task."""
        return self.generate_mock_salary_sheet(query)

class SalarySheetRetrieverAgent(BaseAgent):
    """Agent to retrieve financial data from a salary sheet."""

    def retrieve_financial_data(self, salary_sheet_json: str) -> str:
        """Retrieves key financial data from a given JSON string."""
        print(f"📈 Extracting financial data from salary sheet...")
        try:
            sheet_data = json.loads(salary_sheet_json)
            
            monthly_salary = sheet_data.get('monthly_salary', 0)
            existing_emi = sheet_data.get('existing_emi', 0)
            credit_score = sheet_data.get('credit_score', 0)
            
            credit_rating = "Excellent" if credit_score >= 750 else "Good" if credit_score >= 700 else "Fair" if credit_score >= 650 else "Poor"
            affordability = "High" if monthly_salary > 75000 else "Medium" if monthly_salary > 40000 else "Limited"
            
            retrieved_data = {
                "user_data": sheet_data,
                "financial_assessment": {
                    "credit_rating": credit_rating,
                    "income_level": affordability,
                    "monthly_disposable_income": monthly_salary - existing_emi,
                    "existing_debt_burden": f"₹{existing_emi:,.0f} per month"
                },
                "status": "salary_sheet_data_retrieved_successfully"
            }
            
            print(f"✅ Financial data extraction completed!")
            return json.dumps(retrieved_data, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to retrieve data from salary sheet: {str(e)}"})
            
    def run(self, salary_sheet_json: str) -> str:
        """Runs the agent's specific task."""
        return self.retrieve_financial_data(salary_sheet_json)
