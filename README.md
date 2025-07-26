# 🧠 Agentic AI for Banking, Loans, and Fraud Detection

This project is an **Agentic AI system** for banking, loan processing, and fraud detection, integrating LangChain, LLMs (Google Generative AI, Groq), and human-in-the-loop escalation. It features modular agents, a langchain orchestrator, and a Streamlit UI.

## 📁 Project Structure

```text
├── human_operator_dashboard.py               # CLI dashboard for escalations
├── run_loan_cli.py                           # CLI for loan workflow
├── run_loan_test.py                          # Test runner for agents
├── requirements.txt                          # Python dependencies
├── sample_salary_template.txt/pdf            # Sample templates
├── agentic_ai/                               # Main package
│   ├── core/agent/                           # Agent logic
│   ├── core/config/                          # Configs
│   ├── core/llm/                             # LLM integration
│   ├── core/orchestrator/                    # Workflow orchestrators
│   ├── core/utils/                           # Utilities
│   ├── modules/loan_processing/              # Loan agent modules
│   ├── scripts/                              # Scripts
│   ├── streamlit_app/run_loan_streamlit.py   # Main Streamlit UI
│   └── tests/                                # Unit tests
├── scripts/aadhaar_details_api.py            # Aadhaar API
├── scripts/credit_score_api.py               # Credit Score API
├── streamlit_app/run_loan_streamlit.py       # Streamlit frontend
├── escalation_data/                          # Escalation/session data
```

## 🛠️ Technologies Used

- **Python 3.11.9**
- **LangChain** (LLM orchestration)
- **Google Generative AI, Groq, OpenAI** (LLM backends)
- **Flask** (API)
- **Streamlit** (Frontend UI)
- **Sentence Transformers** (Semantic matching)
- **fuzzywuzzy** (Fuzzy string matching)
- **PyPDF2** (PDF parsing)

## ⚙️ How It Works

1. **Loan Processing Workflow**: Modular agents handle customer, risk, geo-policy, agreement, and more using LLMs and utility modules.
2. **Streamlit UI**: Main user interface for loan application and status tracking.
3. **Human Operator Dashboard**: CLI tool for handling escalated cases when automation fails.
4. **API's**: Aadhaar and Credit Score APIs provide external data for loan processing.

## 🚀 Setup Instructions

### ✅ Prerequisites

- Python 3.11.9
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 🔑 Environment Variables

Set your LLM API keys in a `.env` file:
```env
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_google_api_key
```

## 🏃 How to Run (Multi-Terminal Setup)

You need **4 terminals** running in parallel for full functionality:


### 1️⃣ Aadhaar Details API (Flask)
**File:** `scripts/aadhaar_details_api.py`
```bash
python scripts/aadhaar_details_api.py
# Runs on port 5002
```

### 2️⃣ Credit Score API (Flask)
**File:** `scripts/credit_score_api.py`
```bash
python scripts/credit_score_api.py
# Runs on port 5001
```

### 3️⃣ Main Streamlit App (Frontend)
**File:** `streamlit_app/run_loan_streamlit.py`
```bash
streamlit run streamlit_app/run_loan_streamlit.py
```

### 4️⃣ Human Operator Dashboard (CLI)
**File:** `human_operator_dashboard.py` (or `agentic_ai/human_operator_dashboard.py`)
```bash
python human_operator_dashboard.py
```

---

## 👨‍💼 Human Operator Dashboard

The dashboard is a CLI tool for handling escalated loan cases. It allows human operators to:
- View active escalations (from `escalation_data/active_sessions.json`)
- Respond to cases and provide decisions
- Monitor statistics and view conversation history

**How to use:**
1. Start the dashboard in a terminal:
   ```bash
   python human_operator_dashboard.py
   ```
   Or, if using the package version:
   ```bash
   python agentic_ai/human_operator_dashboard.py
   ```
2. The dashboard will display active sessions and prompt for actions (e.g., approve/reject, add comments).
3. Respond to escalated cases as needed. Your input will be saved and used to resolve the loan workflow. All operator actions are logged in `escalation_data/human_responses.json`.

---

## 📝 Additional Notes

- **Testing:**
  - Run `run_loan_test.py` for agent tests.
  - Unit tests are in `agentic_ai/tests/`.
- **Extensibility:**
  - Add new agents in `agentic_ai/modules/loan_processing/`
  - Update orchestrators in `agentic_ai/core/orchestrator/`
- **Data:**
  - Sample data and templates are in `sample_salary_template.txt`, `sample_salarypdf_template.pdf`, and `uploaded_files/`

---

## 📚 References

- [LangChain Documentation](https://python.langchain.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

## � License

This project is for educational and demonstration purposes.
---
