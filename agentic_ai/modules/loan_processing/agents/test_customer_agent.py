import unittest
from agentic_ai.modules.loan_processing.agents.customer_agent import CustomerAgent

class TestCustomerAgent(unittest.TestCase):
    def setUp(self):
        self.agent = CustomerAgent()

    def test_purpose(self):
        q = "What is the purpose of your loan?"
        response = self.agent.run(q)
        self.assertIsInstance(response, str)
        self.assertIn(response, [self.agent.profile['purpose'], 'personal expenses'])

    def test_amount(self):
        q = "How much loan amount do you need?"
        response = self.agent.run(q)
        self.assertIsInstance(response, str)
        self.assertEqual(response, self.agent.profile['amount'])

    def test_city(self):
        q = "Which city do you live in?"
        response = self.agent.run(q)
        self.assertIsInstance(response, str)
        self.assertEqual(response, self.agent.profile['city'])

    def test_identifier(self):
        q = "Please provide your identifier"
        response = self.agent.run(q)
        self.assertIsInstance(response, str)
        self.assertEqual(response, self.agent.profile['identifier'])

    def test_agreement(self):
        q = "Do you agree to the terms and conditions?"
        response = self.agent.run(q)
        self.assertIn(response, ["I AGREE", "I DECLINE"])

    def test_salary_update(self):
        q = "Do you want to update your salary?"
        response = self.agent.run(q)
        self.assertIn(response, ["yes", "no"])

    def test_pdf_path(self):
        q = "Please provide the path to your salary slip PDF."
        response = self.agent.run(q)
        self.assertIsInstance(response, str)
        self.assertTrue(response.endswith('.pdf') or response.startswith('Sorry'))

    def test_clarification(self):
        q = "What is the purpose of your loan?"
        self.agent.run(q)
        response = self.agent.run(q)
        self.assertIn("clarify", response.lower())

if __name__ == "__main__":
    unittest.main()
