import random
import os
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
        # Add agreement response preference (can be customized per customer)
        self.agreement_response_preference = "accept"  # "accept", "decline", or "random"

    def _generate_random_profile(self):
        # Generate a random but valid customer profile
        purposes = ["home renovation", "education", "wedding", "business expansion", "medical"]
        cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
        
        # Create paired PAN and Aadhaar numbers (from the ACTUAL dataset)
        user_profiles = [
            {"pan": "NAMWT4886W", "aadhaar": "631999289535"},
            {"pan": "AASIL9982X", "aadhaar": "263955468941"},
            {"pan": "OHWQG0796D", "aadhaar": "216563686675"},
            {"pan": "DVNFN2660N", "aadhaar": "747356461632"},
            {"pan": "RFFRX8893L", "aadhaar": "96193980326"},
            {"pan": "TFVIQ8661A", "aadhaar": "467580848845"},
            {"pan": "JOZFF9522G", "aadhaar": "246535477153"},
            {"pan": "GBFLY6345U", "aadhaar": "503153508818"},
            {"pan": "AOGGX0057V", "aadhaar": "347676851687"},
            {"pan": "VNUTM3387Y", "aadhaar": "776849406520"},
            {"pan": "PKHCY6517J", "aadhaar": "960716235487"},
            {"pan": "AJTHJ4957H", "aadhaar": "225812783128"},
            {"pan": "JPYVM1461B", "aadhaar": "324444958446"}
        ]
        
        # Select a random user profile
        selected_profile = random.choice(user_profiles)
        
        # FOR TESTING AADHAAR-FIRST FLOW: Always use Aadhaar as the initial identifier
        # This will force the system to ask for PAN later for credit score verification
        identifier = selected_profile["aadhaar"]  # Always start with Aadhaar
        
        return {
            "purpose": random.choice(purposes),
            "amount": str(random.choice([100000, 250000, 500000, 750000, 1000000])),
            "city": random.choice(cities),
            "identifier": identifier,
            "pan": selected_profile["pan"],
            "aadhaar": selected_profile["aadhaar"]
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
        self._answered_agreement = False  # Track agreement response
        self._answered_pan_after_aadhaar = False  # Track PAN request after Aadhaar
        self._last_salary_update_response = None

    def run(self, question: str = None, **kwargs) -> str:
        """Responds to the system's questions as a user would (compatible signature)."""
        q = (question or "").lower()
        
        # Handle agreement acceptance/rejection prompts
        if self._is_agreement_question(q):
            if not getattr(self, '_answered_agreement', False):
                self._answered_agreement = True
                response = self._get_agreement_response()
                print(f"[CustomerAgent] Agreement question detected. Responding: {response}")
                return response
            else:
                # If asked again, return the same response
                return self._get_agreement_response()
        
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
        if any(k in q.lower() for k in ["pdf", "salary slip", "file path", "document", "provide the path"]):
            if not getattr(self, '_answered_pdf_path', False):
                self._answered_pdf_path = True
            # Return the path regardless, no need for else as it's the same
            return os.path.join(os.getcwd(), "sample_salarypdf_template.pdf")

        
        # Handle NEW FLOW: PAN request after Aadhaar (credit score verification)
        # Be more specific to avoid matching general identifier requests
        if (("pan number" in q and ("credit score" in q or "verification" in q)) or 
           ("pan number required" in q) or 
           ("pan number to fetch" in q) or
           ("pan for credit" in q)) and "aadhaar" not in q:
            # This is the new flow where system asks for PAN after Aadhaar for credit score
            if not getattr(self, '_answered_pan_after_aadhaar', False):
                self._answered_pan_after_aadhaar = True
                
                # Smart PAN mapping: Use database mappings for known Aadhaar numbers
                aadhaar_to_pan_mapping = {
                    "631999289535": "NAMWT4886W",
                    "263955468941": "AASIL9982X", 
                    "216563686675": "OHWQG0796D",
                    "747356461632": "DVNFN2660N",
                    "96193980326": "RFFRX8893L",
                    "467580848845": "TFVIQ8661A",
                    "246535477153": "JOZFF9522G",
                    "503153508818": "GBFLY6345U",
                    "347676851687": "AOGGX0057V",  # This is the problematic one!
                    "776849406520": "VNUTM3387Y",
                    "960716235487": "PKHCY6517J",
                    "225812783128": "AJTHJ4957H",
                    "324444958446": "JPYVM1461B"
                }
                
                # Check if we can find the Aadhaar from our profile or use smart mapping
                current_aadhaar = self.profile.get("aadhaar", self.profile.get("identifier"))
                if current_aadhaar in aadhaar_to_pan_mapping:
                    pan_to_return = aadhaar_to_pan_mapping[current_aadhaar]
                else:
                    # Fallback to profile PAN
                    pan_to_return = self.profile.get("pan", "ABCDE1234F")
                
                print(f"[CustomerAgent] System requesting PAN for credit score verification. Providing: {pan_to_return}")
                return pan_to_return
            else:
                # Return the same PAN if asked again (use same logic)
                aadhaar_to_pan_mapping = {
                    "631999289535": "NAMWT4886W",
                    "263955468941": "AASIL9982X", 
                    "216563686675": "OHWQG0796D",
                    "747356461632": "DVNFN2660N",
                    "96193980326": "RFFRX8893L",
                    "467580848845": "TFVIQ8661A",
                    "246535477153": "JOZFF9522G",
                    "503153508818": "GBFLY6345U",
                    "347676851687": "AOGGX0057V",
                    "776849406520": "VNUTM3387Y",
                    "960716235487": "PKHCY6517J",
                    "225812783128": "AJTHJ4957H",
                    "324444958446": "JPYVM1461B"
                }
                current_aadhaar = self.profile.get("aadhaar", self.profile.get("identifier"))
                if current_aadhaar in aadhaar_to_pan_mapping:
                    return aadhaar_to_pan_mapping[current_aadhaar]
                else:
                    return self.profile.get("pan", "ABCDE1234F")
        
        # Handle PAN/Aadhaar/identifier requests (original flow)
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

    def _is_agreement_question(self, question: str) -> bool:
        """Detects if the question is asking for agreement acceptance/rejection."""
        agreement_keywords = [
            "do you agree", "accept the terms", "loan agreement", "terms and conditions",
            "please accept", "please decline", "agreement", "i agree", "i decline",
            "sign the agreement", "digital signature", "e-signature", "consent"
        ]
        return any(keyword in question.lower() for keyword in agreement_keywords)

    def _get_agreement_response(self) -> str:
        """Returns the agreement response based on the customer's preference."""
        if self.agreement_response_preference == "accept":
            return "I AGREE"
        elif self.agreement_response_preference == "decline":
            return "I DECLINE"
        elif self.agreement_response_preference == "random":
            return random.choice(["I AGREE", "I DECLINE"])
        else:
            # Default to accept
            return "I AGREE"

    def set_agreement_preference(self, preference: str):
        """Set the customer's agreement response preference.
        
        Args:
            preference: "accept", "decline", or "random"
        """
        if preference in ["accept", "decline", "random"]:
            self.agreement_response_preference = preference
        else:
            print(f"[CustomerAgent] Warning: Invalid preference '{preference}'. Using 'accept' as default.")
            self.agreement_response_preference = "accept"
