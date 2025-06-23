# test_loan_processing.py
import unittest
from unittest.mock import patch, MagicMock
from agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator import LoanAgentOrchestrator

class TestLoanProcessing(unittest.TestCase):

    @patch('agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator.LoanDataService')
    @patch('agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator.create_agent_executor')
    def test_process_application_existing_user(self, mock_create_agent_executor, mock_loan_data_service):
        """
        Test the successful processing of an application for an existing user.
        """
        # Arrange
        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {"output": "Loan Approved"}
        mock_create_agent_executor.return_value = mock_executor
        
        orchestrator = LoanAgentOrchestrator()
        
        # Act
        result = orchestrator.process_application("I need a personal loan for 5 lakhs with PAN ABCDE1234F.")
        
        # Assert
        self.assertEqual(result, "Loan Approved")
        mock_executor.invoke.assert_called_once()

    @patch('agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator.LoanDataService')
    @patch('agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator.create_agent_executor')
    def test_process_application_new_user(self, mock_create_agent_executor, mock_loan_data_service):
        """
        Test the successful processing of an application for a new user.
        """
        # Arrange
        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {"output": "Loan Conditionally Approved"}
        mock_create_agent_executor.return_value = mock_executor

        orchestrator = LoanAgentOrchestrator()

        # Act
        result = orchestrator.process_application("New user, need a home loan for 70 lakhs.")

        # Assert
        self.assertEqual(result, "Loan Conditionally Approved")
        mock_executor.invoke.assert_called_once()

if __name__ == '__main__':
    unittest.main()
