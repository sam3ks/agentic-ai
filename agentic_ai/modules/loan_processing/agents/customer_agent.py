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
        self.profile = profile or self._generate_random_profile()
        self.step = 0
        self.agreement_response_preference = "accept"
        self._reset_answer_flags()
 
    def _reset_answer_flags(self):
        self._answered_purpose = False
        self._answered_amount = False
        self._answered_city = False
        self._answered_identifier = False
        self._answered_salary_update = False
        self._answered_pdf_path = False
        self._answered_agreement = False
        self._answered_pan_after_aadhaar = False
        self._last_salary_update_response = None
        self._last_question = None
 
    def _generate_random_profile(self):
        purposes = ["home renovation", "education", "wedding", "business expansion", "medical"]
        cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
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
        selected_profile = random.choice(user_profiles)
        identifier = selected_profile["aadhaar"]
        return {
            "purpose": random.choice(purposes),
            "amount": str(random.choice([100000, 250000, 500000, 750000, 1000000])),
            "city": random.choice(cities),
            "identifier": identifier,
            "pan": selected_profile["pan"],
            "aadhaar": selected_profile["aadhaar"]
        }
 
    def reset_state(self):
        self._reset_answer_flags()
 
    def update_profile(self, updates: dict):
        if not self.profile:
            self.profile = {}
        for k, v in (updates or {}).items():
            if v and v != "unknown":
                self.profile[k] = str(v)
 
    def set_initial_details(self, details: dict):
        if not self.profile:
            self.profile = {}
        for k in ("purpose", "amount", "city"):
            v = (details or {}).get(k)
            if v and v != "unknown":
                self.profile[k] = str(v)
        if "identifier" in details:
            self.profile["identifier"] = str(details["identifier"])
 
    def run(self, question: str = None, **kwargs) -> str:
        q = (question or "").lower()
        if self._last_question == q:
            return "Could you please clarify your question?"
        self._last_question = q
        
        if self._is_agreement_question(q):
            if not getattr(self, '_answered_agreement', False):
                self._answered_agreement = True
                response = self._get_agreement_response()
                print(f"[CustomerAgent] Agreement question detected. Responding: {response}")
                return response
            else:
                return self._get_agreement_response()
 
        if ("update" in q and "salary" in q) or ("want to update" in q and "salary" in q):
            if not getattr(self, '_answered_salary_update', False):
                self._answered_salary_update = True
                self._last_salary_update_response = random.choice(["yes", "no"])
                return self._last_salary_update_response
            else:
                return self._last_salary_update_response or "yes"
        
        if ("pdf" in q or "salary slip" in q or "file path" in q or "document" in q or "provide the path" in q):
            import os
            if not getattr(self, '_answered_pdf_path', False):
                self._answered_pdf_path = True
                # Path to main folder where the PDF will be kept
                main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                pdf_path = os.path.join(main_dir, "sample_salarypdf_template.pdf")
                return pdf_path if os.path.exists(pdf_path) else "Sorry, I can't find the file. Please specify another path."
            else:
                main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                return os.path.join(main_dir, "sample_salarypdf_template.pdf")
 
        if (("pan number" in q and ("credit score" in q or "verification" in q)) or
            ("pan number required" in q) or
            ("pan number to fetch" in q) or
            ("pan for credit" in q)) and "aadhaar" not in q:
            if not getattr(self, '_answered_pan_after_aadhaar', False):
                self._answered_pan_after_aadhaar = True
                aadhaar_to_pan_mapping = {
                    "631999289535": "NAMWT4886W",
                    "263955468941": "AASIL9982X",
                    "216563686675": "OHWQG0796D",
                    "747356461632": "DVNFN2660N",
                    "96193980326":  "RFFRX8893L",
                    "467580848845": "TFVIQ8661A",
                    "246535477153": "JOZFF9522G",
                    "503153508818": "GBFLY6345U",
                    "347676851687": "AOGGX0057V",
                    "776849406520": "VNUTM3387Y",
                    "960716235487": "PKHCY6517J",
                    "225812783128": "AJTHJ4957H",
                    "324444958446": "JPYVM1461B"
                }
                current_aadhaar = str(self.profile.get("aadhaar", self.profile.get("identifier")))
                pan_to_return = aadhaar_to_pan_mapping.get(current_aadhaar, self.profile.get("pan", "ABCDE1234F"))
                print(f"[CustomerAgent] System requesting PAN for credit score verification. Providing: {pan_to_return}")
                return str(pan_to_return)
            else:
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
                current_aadhaar = str(self.profile.get("aadhaar", self.profile.get("identifier")))
                return str(aadhaar_to_pan_mapping.get(current_aadhaar, self.profile.get("pan", "ABCDE1234F")))
 
        # If the system asks for PAN (by format or explicit keyword), return PAN
        if ("pan" in q and ("number" in q or "pan" in q or "ABCDE1234F" in q)) or ("pan or aadhaar" in q):
            # Always use the PAN from the generated profile if available
            pan_value = self.profile.get("pan")
            if pan_value and pan_value != "ABCDE1234F":
                self._answered_identifier = True
                return str(pan_value)
            else:
                # fallback only if profile PAN is missing
                self._answered_identifier = True
                return "ABCDE1234F"
        # If the system asks for Aadhaar specifically
        if "aadhaar" in q and not "pan" in q:
            return str(self.profile.get("aadhaar", "123456789012"))
        # If the system asks for identifier in a generic way, return identifier
        if "identifier" in q:
            return str(self.profile.get("identifier", "ABCDE1234F"))
 
        if "purpose" in q:
            return str(self.profile.get("purpose", "personal expenses"))
 
        if "amount" in q:
            if not getattr(self, '_answered_amount', False):
                self._answered_amount = True
                return str(self.profile.get("amount", "100000"))
            else:
                return str(self.profile.get("amount", "100000"))
 
        if "city" in q:
            if not getattr(self, '_answered_city', False):
                self._answered_city = True
                return str(self.profile.get("city", "Mumbai"))
            else:
                return str(self.profile.get("city", "Mumbai"))
 
        return "Sorry, could you please clarify your question?"
 
    def handle_user_input(self, question: str) -> str:
        return self.run(question)
 
    def _is_agreement_question(self, question: str) -> bool:
        agreement_keywords = [
            "do you agree", "accept the terms", "loan agreement", "terms and conditions",
            "please accept", "please decline", "agreement", "i agree", "i decline",
            "sign the agreement", "digital signature", "e-signature", "consent"
        ]
        return any(keyword in question.lower() for keyword in agreement_keywords)
 
    def _get_agreement_response(self) -> str:
        if self.agreement_response_preference == "accept":
            return "I AGREE"
        elif self.agreement_response_preference == "decline":
            return "I DECLINE"
        elif self.agreement_response_preference == "random":
            return random.choice(["I AGREE", "I DECLINE"])
        else:
            return "I AGREE"
 
    def set_agreement_preference(self, preference: str):
        if preference in ["accept", "decline", "random"]:
            self.agreement_response_preference = preference
        else:
            print(f"[CustomerAgent] Warning: Invalid preference '{preference}'. Using 'accept' as default.")
            self.agreement_response_preference = "accept"