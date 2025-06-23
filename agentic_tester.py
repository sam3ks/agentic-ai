# agentic_tester.py

import json

class AgenticTester:
    def __init__(self, agent):
        self.agent = agent
        self.logs = []

    def run_test_flow(self, test_name, messages):
        print(f"\n🧪 Running Test: {test_name}")
        self.agent.context.reset()
        test_results = []

        for idx, step in enumerate(messages, 1):
            user_input = step["input"]
            expected = step.get("expect")

            print(f"👤 [{idx}] User: {user_input}")
            response = self.agent.process_conversation_turn(user_input)
            print(f"🤖 Response: {response}\n")

            passed = expected.lower() in response.lower() if expected else True
            result = {
                "step": idx,
                "input": user_input,
                "response": response,
                "expected": expected,
                "passed": passed
            }

            test_results.append(result)
            self.logs.append((test_name, result))

            if not passed:
                print(f"❌ Failed: Expected to find '{expected}' in response.")

        return test_results

    def summary(self):
        print("\n📊 Test Summary:")
        passed = sum(1 for _, log in self.logs if log["passed"])
        total = len(self.logs)
        print(f"✅ Passed: {passed} | ❌ Failed: {total - passed} | 🔢 Total: {total}")

    def load_test_flows_from_json(self, filepath):
        with open(filepath, "r") as f:
            return json.load(f)

# agentic_tester.py

import json

class AgenticTester:
    def __init__(self, agent):
        self.agent = agent
        self.logs = []

    def run_test_flow(self, test_name, messages):
        print(f"\n🧪 Running Test: {test_name}")
        self.agent.context.reset()
        test_results = []

        for idx, step in enumerate(messages, 1):
            user_input = step["input"]
            expected = step.get("expect")

            print(f"👤 [{idx}] User: {user_input}")
            response = self.agent.process_conversation_turn(user_input)
            print(f"🤖 Response: {response}\n")

            passed = expected.lower() in response.lower() if expected else True
            result = {
                "step": idx,
                "input": user_input,
                "response": response,
                "expected": expected,
                "passed": passed
            }

            test_results.append(result)
            self.logs.append((test_name, result))

            if not passed:
                print(f"❌ Failed: Expected to find '{expected}' in response.")

        return test_results

    def summary(self):
        print("\n📊 Test Summary:")
        passed = sum(1 for _, log in self.logs if log["passed"])
        total = len(self.logs)
        print(f"✅ Passed: {passed} | ❌ Failed: {total - passed} | 🔢 Total: {total}")

    def load_test_flows_from_json(self, filepath):
        with open(filepath, "r") as f:
            return json.load(f)
