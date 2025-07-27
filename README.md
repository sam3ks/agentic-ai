# 🧠 Agentic AI for Banking, Loans, and Fraud Detection

This project is an **Agentic AI system** for banking, loan processing, and fraud detection, built with LangChain, LangGraph, and LLMs (Groq, OpenAI). It features modular agents, robust session management, CLI and Streamlit frontends, and escalation to human operators.

---

## 📁 Project Structure & Key Modules

```
agentic_ai/
  core/
    agent/           # Abstract and base agent classes
    config/          # Constants, config loader, logger, reliability
    llm/             # LLM wrappers (Groq, OpenAI, Ollama), factory
    orchestrator/    # Workflow orchestration (StateGraph, agent executor)
    session/         # Persistent session management
    utils/           # Formatting, fuzzy matching, monitoring, parsing, validators
  modules/
    loan_processing/
      agents/        # Specialized agents: user interaction, data query, geo-policy, risk, agreement, salary extraction, escalation, human
      app/           # CLI entrypoint for loan processing
      data/          # Loan policy JSON, sample loan dataset
      orchestrator/  # Main orchestrator, escalation orchestrator
      services/      # Data service, PDF parser
      prompts/       # Prompt templates
      tests/         # Test cases for loan processing
  scripts/           # Utility scripts (rate limit verification, Aadhaar, credit score)
docs/                # Architecture documentation
streamlit_app/       # Streamlit frontend for loan workflow
session_data/        # Persistent session files
escalation_data/     # Human escalation session and response files
test_flows/          # Example flows for testing
uploaded_files/      # Uploaded salary PDFs
human_operator_dashboard.py # CLI dashboard for human escalation
run_loan_cli.py      # CLI entrypoint for loan processing
requirements.txt     # Python dependencies
LICENSE, README.md   # License and documentation
```

---

## 🚀 Setup Instructions

1. **Python 3.11.9** required.
2. Install dependencies:
   ```
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Set environment variables in `.env`:
   ```
   OPENAI_API_KEY=your_openai_api_key
   GROQ_API_KEY=your_groq_api_key
   ```
4. Run the CLI:
   ```
   python run_loan_cli.py
---

## 🏗️ Main Components

- **Loan Processing Workflow**: Modular agents for user interaction, data query, geo-policy validation, risk assessment, agreement presentation, salary extraction, and escalation.
- **Session Management**: Persistent sessions (resume, list, status) via `SessionManager`.
- **CLI Frontend**: `run_loan_cli.py` for interactive or automated loan processing.
- **Human Escalation**: Automated escalation to human operators via dashboard if agents fail.
- **Data & Policy**: Loan purpose policy (`loan_purpose_policy.json`), sample loans (`sample_loans.csv`).


## 💡 Capabilities

- **Banking Agent**: Account, card, transaction services.
- **Fraud Agent**: Risk score analysis, anomaly detection, compliance checks.
- **Loan Agent**: Credit risk profiling, EMI affordability, geo-policy checks.
- **Session Management**: Resume, list, and status of loan sessions.
- **Human Escalation**: Operator dashboard for unresolved cases.

---

## 📌 Notes

## ⏸️ How to Interrupt and Resume a Loan Session (Step-by-Step)

You can interrupt a loan session at any time and resume it later using the CLI. This is useful for long workflows or when you need to pause and continue later.

### Interrupting a Session
1. **Start a loan session** using the CLI:
   ```
   python run_loan_cli.py
   ```
2. **At any prompt**, press `Ctrl+C` to pause the session.
3. The session state will be saved automatically in the `session_data/` folder as a JSON file (named with timestamp and session ID).

### Resuming a Session

1. **Resume a session** by providing the session ID:
   ```
   python run_loan_cli.py <session_id>
   ```
   Replace `<session_id>` with the actual ID from the loan session which was paused.
3. The workflow will continue from where you left off.

### Additional Tips
- You can check the status of a session:
  ```
  python run_loan_cli.py --status <session_id>
  ```
- All session files are stored in `session_data/`.
- Interrupted sessions can be resumed multiple times until completed.

---

---

## 📃 License

This project is for educational and demonstration purposes.

---
