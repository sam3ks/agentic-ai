# 🧠 Integrated Agentic AI for Banking, Loans, and Fraud Detection

This project is an **Agentic AI system** combining banking services, fraud detection, and loan processing using LangChain and LLMs like Google Generative AI and Groq. It provides autonomous decision-making capabilities through natural language interaction.

---

## 📁 Project Structure

```text
├── Main.py                 # Orchestrator to manage conversations and route intents
├── Banking.py              # Account, card, and transaction services
├── Fraud.py               # Fraud detection and AML compliance agents
├── Loan.py                # Loan risk, geo-policy, and financial eligibility
├── requirements.txt        # All Python dependencies
```

---

## 🚀 Setup Instructions

### ✅ Prerequisites

- Python 3.10 (e.g., installed at: `C:\Users\<<user>>\AppData\Local\Programs\Python\Python310`)
- [Groq API Key](https://console.groq.com/)
- [Google Generative AI API Key](https://ai.google.dev/)
- Internet connection to use LLM APIs

---

### 🔧 1. Create and Activate Virtual Environment

```bash
C:\Users\<<user>>\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv
.venv\Scripts\activate
```

---

### 📦 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 🔐 3. Set Environment Variables

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_api_key
GROQ_API_KEY=your_groq_api_key
```

---

### ▶️ 4. Run the Application

```bash
python Main.py
```

---

## 💡 Capabilities

- 🏦 **Banking Agent**: Balance inquiry, mini statements, internal transfers, KYC updates
- 🔍 **Fraud Agent**: Risk score analysis, anomaly detection, document & compliance checks
- 💳 **Loan Agent**: Credit risk profiling, EMI affordability, location-based policy checks
- 🧠 **LLM-based Reasoning**: Uses LangChain agents and Groq/Google APIs for decision making

---

## 📌 Notes

- The `Fraud_detect.csv` and `Loan_Dataset_V1.csv` should be in the same directory if required.
- Some agents prompt the user for input in the terminal.
- You can expand this setup into a REST API or GUI.

---

## 📃 License

This project is for educational and demonstration purposes.

---

# Agentic AI

An intelligent agentic AI system for banking that autonomously handles account creation, loan processing, fraud detection, and customer queries through natural conversation and context-aware flows.
