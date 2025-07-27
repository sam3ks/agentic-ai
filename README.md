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

## 🐳 Dockerized Microservices Setup

This project includes containerized FastAPI microservices for:
- **Aadhaar Verification API**
- **Credit Score API**
- **Streamlit Loan UI**
- **Human Operator Dashboard**

### 📦 Prerequisites

Install Docker and Docker Compose:

```bash
sudo apt update
sudo apt install docker.io docker-compose -y
```

---

### 📁 Docker Structure

```
services/
├── aadhaar_api/           # Aadhaar FastAPI service
├── credit_score_api/      # Credit Score FastAPI service
docker-compose.yml         # Compose file to run everything together
```

Each microservice contains:
- `main.py`: FastAPI app entrypoint
- `app/`: route handlers and logic
- `requirements.txt`: service dependencies
- `Dockerfile`: Docker image setup

---

### ▶️ Build and Run the Project

From the project root directory:

```bash
# Build all containers
docker compose build --no-cache

# Start all services in background
docker compose up -d
```

Check running containers:

```bash
docker ps
```

---

### 🌐 Service URLs (Defaults)

- Aadhaar API → http://localhost:5002/aadhaar/verify?aadhaar_number=123456789012  
- Credit Score API → http://localhost:5001/credit-score?customer_id=123  
- Streamlit Loan UI → http://localhost:8501  
- Human Dashboard (CLI) → `python human_operator_dashboard.py`

---

### 📄 View Logs

```bash
docker compose logs -f aadhaar_api
docker compose logs -f credit_score_api
docker compose logs -f streamlit_ui
```

---

### 🛑 Stop & Clean

```bash
# Stop services
docker compose down

# Optionally remove all containers
docker rm -f $(docker ps -aq)
```


---

## 📃 License

This project is for educational and demonstration purposes.

---
