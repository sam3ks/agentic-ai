import random
from agentic_ai.core.agent.base_agent import BaseAgent

class CustomerAgent(BaseAgent):
    """
    Automated agent that mimics a user by providing required details (purpose, amount, city, PAN/Aadhaar)
    to the loan processing workflow. Useful for automation, testing, and demos.
    """
    
    def __init__(self, profile=None):
        super().__init__()
        # Default or custom profile for the customer
        self.profile = profile or self._generate_random_profile()
        self.step = 0  # Track which info to provide next

    def _generate_random_profile(self):
        # Generate a random but valid customer profile
        purposes = ["home renovation", "education", "wedding", "business expansion", "medical"]
        cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
        pan_numbers = ["ABCDE1234F", "FGHIJ5678K", "KLMNO9012P", "AASIL9982X" ,"OHWQG0796D", "JPYVM1461B"]
        aadhaar_numbers = ["123456789012", "234567890123", "345678901234","503153508818","347676851687","776849406520"]
        return {
            "purpose": random.choice(purposes),
            "amount": str(random.choice([100000, 250000, 500000, 750000, 1000000])),
            "city": random.choice(cities),
            "identifier": random.choice(pan_numbers + aadhaar_numbers)
        }

    def reset_state(self):
        """Resets the state of the agent (for compatibility with orchestrator)."""
        self.step = 0
        self._answered_purpose = False
        self._answered_amount = False
        self._answered_city = False
        self._answered_identifier = False
        self._answered_salary_update = False
        self._answered_pdf_path = False
        self._last_salary_update_response = None

    def run(self, question: str = None, **kwargs) -> str:
        """Responds to the system's questions as a user would (compatible signature)."""
        q = (question or "").lower()
        # Handle salary update prompt
        if ("update" in q and "salary" in q) or ("want to update" in q and "salary" in q):
            if not getattr(self, '_answered_salary_update', False):
                self._answered_salary_update = True
                # Randomly decide yes/no, or always yes for demo
                self._last_salary_update_response = random.choice(["yes", "no"])
                return self._last_salary_update_response
            else:
                return self._last_salary_update_response or "yes"
        # Handle PDF path prompt
        if ("pdf" in q or "salary slip" in q or "file path" in q or "document" in q or "provide the path" in q):
            if not getattr(self, '_answered_pdf_path', False):
                self._answered_pdf_path = True
                return r"C:\Users\R.Darshan\Downloads\Agentic_AI_main_v8 (1)\Agentic_AI_main_v8\Agentic_AI_main_v5\agentic-ai-main\agentic_ai\sample_salarypdf_template.pdf"
            else:
                return r"C:\Users\R.Darshan\Downloads\Agentic_AI_main_v8 (1)\Agentic_AI_main_v8\Agentic_AI_main_v5\agentic-ai-main\agentic_ai\sample_salarypdf_template.pdf"
        # Handle PAN/Aadhaar
        if "pan" in q or "aadhaar" in q or "identifier" in q:
            if not getattr(self, '_answered_identifier', False):
                self._answered_identifier = True
                return self.profile.get("identifier", "ABCDE1234F")
            else:
                return self.profile.get("identifier", "ABCDE1234F")
        # Handle purpose (always return the same purpose for the session)
        if "purpose" in q:
            return self.profile.get("purpose", "personal expenses")
        # Handle amount
        if "amount" in q:
            if not getattr(self, '_answered_amount', False):
                self._answered_amount = True
                return self.profile.get("amount", "100000")
            else:
                return self.profile.get("amount", "100000")
        # Handle city
        if "city" in q:
            if not getattr(self, '_answered_city', False):
                self._answered_city = True
                return self.profile.get("city", "Mumbai")
            else:
                return self.profile.get("city", "Mumbai")
        # Default: return a random value
        return random.choice(list(self.profile.values()))
    
    def set_initial_details(self, details: dict):
        """Sets the initial details extracted from the user's first message (for compatibility).
        Ensures the agent's profile matches the initial request for consistency."""
        if not self.profile:
            self.profile = {}
        # Always override profile with initial details if present and valid
        for k in ("purpose", "amount", "city"):
            v = (details or {}).get(k)
            if v and v != "unknown":
                self.profile[k] = v
        # Identifier is not always in the initial request, so keep as is if not present
        if "identifier" in details:
            self.profile["identifier"] = details["identifier"]

    def handle_user_input(self, question: str) -> str:
        """Handles user interaction by mimicking user input for automation."""
        # This agent does not prompt, it just returns the appropriate value
        return self.run(question)
