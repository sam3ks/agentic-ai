# account_type_mapper.py
from sentence_transformers import SentenceTransformer, util

class AccountTypeMapper:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.valid_account_types = {
            "savings": ["savings", "savings account", "save", "basic", "individual", "salary", "saver"],
            "current": ["current", "current account", "corporate", "business", "enterprise", "firm", "company", "checking"],
            "joint": ["joint", "shared", "couple", "family", "two-person"],
            "Fixed Deposit": ["fixed deposit", "term deposit", "fd"]
        }
        self.flattened_phrases = []
        self.type_lookup = []
        for acc_type, phrases in self.valid_account_types.items():
            for p in phrases:
                self.flattened_phrases.append(p)
                self.type_lookup.append(acc_type)
        self.embeddings = self.model.encode(self.flattened_phrases, convert_to_tensor=True)

    def resolve(self, user_input):
        user_emb = self.model.encode(user_input, convert_to_tensor=True)
        scores = util.pytorch_cos_sim(user_emb, self.embeddings)[0]
        best_idx = scores.argmax().item()
        best_score = scores[best_idx].item()
        if best_score >= 0.6:
            return self.type_lookup[best_idx]
        else:
            top_scores = sorted([(self.type_lookup[i], scores[i].item()) for i in range(len(scores))], key=lambda x: -x[1])[:3]
            print(f"⚠️ Could not resolve '{user_input}'. Closest guesses: {top_scores}")
            raise ValueError("Unable to resolve account type")
