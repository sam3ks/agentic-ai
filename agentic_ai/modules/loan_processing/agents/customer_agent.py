import random
import os
from agentic_ai.core.agent.base_agent import BaseAgent

class CustomerAgent(BaseAgent):
    """
    Automated agent that mimics a user by providing required details
    (purpose, amount, city, PAN/Aadhaar) for loan processing workflows.
    Useful for automation, testing, and demos.
    Now enhanced to mimic real human quirks.
    """

    def __init__(self, profile: dict = None, pdf_path: str = None):
        super().__init__()
        self.profile = profile or self._generate_random_profile()
        self.step = 0
        self.pdf_path = pdf_path or os.path.join(os.getcwd(), "sample_salary_template.pdf")
        self._memory = {}
        self.reset_state()
        

    def _generate_random_profile(self) -> dict:
        purposes = ["home renovation", "education", "wedding", "business expansion", "medical"]
        cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
        pan_numbers = ["ABCDE1234F", "FGHIJ5678K", "KLMNO9012P", "AASIL9982X", "OHWQG0796D", "JPYVM1461B"]
        aadhaar_numbers = ["123456789012", "234567890123", "345678901234", "503153508818", "347676851687", "776849406520"]
        return {
            "purpose": random.choice(purposes),
            "amount": str(random.choice([100000, 250000, 500000, 750000, 1000000])),
            "city": random.choice(cities),
            "identifier": random.choice(pan_numbers + aadhaar_numbers)
        }

    def reset_state(self) -> None:
        self.step = 0
        self._answered = {}
        self._last_salary_update_response = None
        self._memory.clear()
        self._num_tries = {}

    def _fuzzy_typo(self, value: str) -> str:
        # Simulate a typo in city names or amounts
        if random.random() < 0.08 and value.lower() == "bangalore":
            return "Bangaluru"
        if random.random() < 0.1 and value.isdigit():
            return f"{int(value):,}"  # Format as 1,00,000
        return value

    def _maybe_smalltalk(self):
        responses = [
            "",  # Usually says nothing extra
            "Sure, one moment.",
            "Let me check.",
            "Yeah, I can help with that.",
            "Is this for home loan or something else?",
        ]
        return random.choice(responses) if random.random() < 0.15 else ""

    def run(self, question: str = None, **kwargs) -> str:
        q = (question or "").lower().strip()
        resp = None
        # Small talk sometimes
        prefix = self._maybe_smalltalk()

        # Handle remembering how many times a question is asked
        if q not in self._num_tries:
            self._num_tries[q] = 1
        else:
            self._num_tries[q] += 1

        # Sometimes return "I already gave you that" on repeated asks
        if self._num_tries[q] > 2 and random.random() < 0.3:
            return prefix + " I already shared that info."

        # Simulate clarifying questions
        if "salary" in q and "update" in q and random.random() < 0.1:
            return prefix + " Sorry, do you mean my current employer's salary slip?"

        # Purpose
        if "purpose" in q:
            if random.random() < 0.2:
                resp = "It's for my house."  # Vague
            else:
                resp = self.profile["purpose"]

        # Amount (sometimes use formatted)
        elif "amount" in q:
            val = self.profile["amount"]
            resp = self._fuzzy_typo(val)

        # City (simulate typo sometimes)
        elif "city" in q:
            resp = self._fuzzy_typo(self.profile["city"])

        # PAN/Aadhaar (sometimes typo, sometimes refuse)
        elif any(k in q for k in ["pan", "aadhaar", "identifier"]):
            if random.random() < 0.1:
                resp = "Can I give that later?"
            else:
                resp = self.profile["identifier"]

        # Salary update (sometimes hesitate/change answer)
        elif "update" in q and "salary" in q:
            if self._last_salary_update_response is None or random.random() < 0.2:
                self._last_salary_update_response = random.choice(["yes", "no"])
            resp = self._last_salary_update_response

        # PDF path (sometimes typo in path)
        elif any(k in q for k in ["pdf", "salary slip", "file path", "document", "provide the path"]):
            if random.random() < 0.1:
                resp = self.pdf_path.replace("sample_salary_template", "sample_slary_tmplate")  # typo
            else:
                resp = self.pdf_path

        # Sometimes answer out of order
        elif random.random() < 0.12:
            resp = random.choice([self.profile["purpose"], self.profile["amount"], self.profile["city"]])

        else:
            resp = random.choice(list(self.profile.values()))

        # Occasionally forget and need to be reminded
        if resp and random.random() < 0.05:
            return prefix + " Sorry, can you repeat the question?"

        return prefix + " " + resp if prefix else resp

    def set_initial_details(self, details: dict) -> None:
        for k in ("purpose", "amount", "city"):
            v = (details or {}).get(k)
            if v and v != "unknown":
                self.profile[k] = v
        if "identifier" in details:
            self.profile["identifier"] = details["identifier"]

    def handle_user_input(self, question: str) -> str:
        return self.run(question)
