# run_agentic_tests.py

from Main import OrchestrationAgent
from agentic_tester import AgenticTester

# Initialize the agent and tester
agent = OrchestrationAgent()
tester = AgenticTester(agent)

# Load and run JSON-defined test flow
test_flow = tester.load_test_flows_from_json("test_flows/account_creation.json")
tester.run_test_flow(test_flow["test_name"], test_flow["steps"])
tester.summary()
