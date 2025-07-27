
# 🧠 Agentic AI for Banking, Loans, and Fraud Detection

This project is an **Agentic AI system** for banking, loan processing, and fraud detection, built with LangChain, LangGraph, and LLMs (Groq, OpenAI). It features modular agents, robust session management, CLI and Streamlit frontends, and escalation to human operators.

---

## 📁 Project Structure & Key Modules

```
agentic_ai/
  core/
  modules/
  scripts/
  docs/
  streamlit_app/
  session_data/
  escalation_data/
  test_flows/
  uploaded_files/
  services/
    aadhaar_api/
      ├── main.py
      ├── routes.py
      ├── Dockerfile
      ├── requirements.txt
      └── aadhaar_details.db
    credit_score_api/
      ├── main.py
      ├── routes.py
      ├── Dockerfile
      ├── requirements.txt
      └── credit_scores.db
  docker/
    streamlit_ui/
    dashboard/
  docker-compose.yml
  .env
  run_loan_cli.py
  human_operator_dashboard.py
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
   GOOGLE_API_KEY=your_google_api_key
   ```
4. Run the CLI:
   ```
   python run_loan_cli.py
   ```

---

## 🏗️ Main Components

- **Loan Processing Workflow**: Modular agents for user interaction, data query, geo-policy validation, risk assessment, agreement presentation, salary extraction, and escalation.
- **Session Management**: Persistent sessions (resume, list, status) via `SessionManager`.
- **CLI Frontend**: `run_loan_cli.py` for interactive or automated loan processing.
- **Human Escalation**: Automated escalation to human operators via dashboard if agents fail.
- **Data & Policy**: Loan purpose policy (`loan_purpose_policy.json`), sample loans (`sample_loans.csv`).

---

## 💡 Capabilities

- **Banking Agent**: Account, card, transaction services.
- **Fraud Agent**: Risk score analysis, anomaly detection, compliance checks.
- **Loan Agent**: Credit risk profiling, EMI affordability, geo-policy checks.
- **Session Management**: Resume, list, and status of loan sessions.
- **Human Escalation**: Operator dashboard for unresolved cases.

---

## ⏸️ How to Interrupt and Resume a Loan Session

1. Run CLI:
   ```
   python run_loan_cli.py
   ```
2. Press `Ctrl+C` to interrupt. The session is saved in `session_data/`.
3. Resume session:
   ```
   python run_loan_cli.py <session_id>
   ```

---

## 🐳 Dockerized Microservices Setup

This project includes containerized **FastAPI microservices using `uv`** for:
- Aadhaar Verification
- Credit Score
- Streamlit UI
- Human Dashboard

---

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
├── aadhaar_api/
├── credit_score_api/
docker-compose.yml
```

Each service includes:
- `main.py`: FastAPI entrypoint
- `routes.py`: Endpoint definitions
- `aadhaar_details.db` / `credit_scores.db`: SQLite data
- `Dockerfile`: Uses `uv` for fast dependency management
- `requirements.txt`: List of dependencies

---

### ▶️ Run All Containers

```bash
docker compose up -d --build
```

To rebuild without cache:
```bash
docker compose build --no-cache
```

---

### 🌐 Service URLs (Defaults)

- Aadhaar API → http://localhost:5002/get_aadhaar_details  
- Credit Score API → http://localhost:5001/get_credit_score  
- Streamlit UI → http://localhost:8501  
- Human Dashboard → `python human_operator_dashboard.py`

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
docker compose down
docker rm -f $(docker ps -aq)  # Optional: removes all containers
```

---

## 🛠️ Troubleshooting

- Ensure `.env` has all required API keys (`OPENAI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`).
- Use `docker ps` to check running containers.
- Ensure databases (`*.db`) are copied in your Docker context.

---

## 📃 License

This project is for educational and demonstration purposes.

---
