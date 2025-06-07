import pandas as pd
import os
import json
from groq import Groq
from datetime import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
import warnings

# LangChain imports
from langchain.agents import Tool, AgentExecutor, create_tool_calling_agent
from langchain.memory import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_core.runnables.history import RunnableWithMessageHistory

# Suppress LangChain deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class Fraud_AML_Agent:
    def __init__(self):
        # Print library versions for debugging
        import langchain
        import langchain_core
        import langchain_groq
        print(f"LangChain version: {langchain.__version__}")
        print(f"LangChain Core version: {langchain_core.__version__}")
        try:
            print(f"LangChain Groq version: {langchain_groq.__version__}")
        except AttributeError:
            print("LangChain Groq version: Not available (version attribute not found)")

        # Initialize Groq client
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("ERROR: GROQ_API_KEY environment variable not set.")
            self.client = None
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                print("Groq client initialized successfully.")
            except Exception as e:
                print(f"ERROR: Failed to initialize Groq client: {e}")
                self.client = None

        # Load dataset and preprocess
        self.df: Optional[pd.DataFrame] = None
        self.required_columns = [
            'TransactionID', 'User_ID', 'TransactionAmt', 'isFraud', 'TransactionDT',
            'Country', 'Is_Cross_Border', 'DeviceInfo', 'KYC_Verified', 'PEP_Flag',
            'Blacklist_Status'
        ]
        dataset_path = os.getenv("Fraud_detect.csv", "Fraud_detect.csv")
        if not os.path.exists(dataset_path):
            print(f"ERROR: Dataset file {dataset_path} not found.")
        else:
            try:
                self.df = pd.read_csv(dataset_path)
                missing_columns = [col for col in self.required_columns if col not in self.df.columns]
                if missing_columns:
                    print(f"ERROR: Missing columns in dataset: {missing_columns}")
                    self.df = None
                else:
                    print("Dataset loaded successfully.")
                    print("Dataset shape:", self.df.shape)
                    self.df['User_ID_str'] = self.df['User_ID'].astype(str)
            except Exception as e:
                print(f"ERROR: An error occurred while loading the dataset: {e}")

        # Initialize sub-agents
        self.conversational_agent = self.ConversationalAgent(self.client)
        self.intent_classifier = self.IntentClassificationAgent(self.client)
        self.transaction_summarization_agent = self.TransactionSummarizationAgent(self.client)
        self.risk_assessment_agent = self.RiskAssessmentAgent(self.client)
        self.document_verification_agent = self.DocumentVerificationAgent(self.client)
        self.cross_border_compliance_agent = self.CrossBorderComplianceAgent(self.client)
        self.advanced_ai = self.LangChainConversationalAgent(self.client, self._create_langchain_tools())

        # Initialize conversation history
        self.conversation_history = []

    # --- Base Agent ---
    class BaseAgent:
        def __init__(self, name: str, groq_client: Any):
            self.name = name
            self.groq_client = groq_client

        def _call_llm(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
            if not self.groq_client:
                return "I'm sorry, but my AI capabilities are currently limited. I can still help with basic fraud detection queries using rule-based analysis."
            try:
                self.log_interaction("Calling LLM", {"prompt": prompt[:50] + "...", "max_tokens": max_tokens})
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama3-8b-8192",
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                result = chat_completion.choices[0].message.content
                self.log_interaction("LLM Response", {"response": result[:50] + "..."})
                return result
            except Exception as e:
                error_msg = f"I apologize, but I'm having trouble processing your request right now. Error: {e}"
                self.log_interaction("LLM Error", {"error": error_msg})
                return error_msg

        def log_interaction(self, action: str, details: Dict[str, Any]) -> None:
            print(f"[Agent: {self.name}] {action}: {details}")

    # --- Conversational Agent ---
    class ConversationalAgent(BaseAgent):
        def __init__(self, groq_client: Any):
            super().__init__("Conversational AI Agent", groq_client)

        def respond_to_greeting(self, user_input: str) -> str:
            greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "greetings"]
            if any(greeting in user_input.lower() for greeting in greetings):
                responses = [
                    "Hello! 👋 I'm your AI-powered Fraud Detection and AML Compliance assistant. How can I help you today?",
                    "Hi there! 🛡️ Welcome to the Advanced Fraud Detection System. I'm here to assist you with user transaction analysis, risk assessment, and much more!",
                    "Greetings! 🚀 I'm your intelligent fraud detection companion. Whether you need to investigate user transactions, analyze patterns, or just have a chat, I'm here for you!"
                ]
                import random
                return random.choice(responses)
            return None

        def handle_general_conversation(self, user_input: str) -> str:
            if not self.groq_client:
                return "I'd love to chat, but my conversational abilities are limited without the AI engine. However, I can still help you with fraud detection tasks!"

            prompt = f"""
            You are an intelligent, friendly AI assistant specializing in fraud detection and AML compliance, but also capable of general conversation.
            The user said: "{user_input}"

            Respond naturally and helpfully. If it's a general question or conversation, engage warmly.
            If it relates to fraud detection, transactions, or financial security, politely ask for their User ID to fetch transaction data automatically.
            If it's about something completely different, be helpful and then gently mention your specialty in fraud detection.

            Keep your response conversational, informative, and engaging. Use emojis where appropriate.
            """

            return self._call_llm(prompt, max_tokens=300, temperature=0.8)

    # --- Intent Classification Agent ---
    class IntentClassificationAgent(BaseAgent):
        def __init__(self, groq_client: Any):
            super().__init__("Intent Classification Agent", groq_client)

        def classify_user_intent(self, user_input: str) -> Dict[str, Any]:
            self.log_interaction("Classifying Intent", {"user_input": user_input[:100] + "..."})
            user_input_lower = user_input.lower()

            # Define intent patterns
            fraud_keywords = ["investigate", "fraud", "transaction", "anomaly", "suspicious", "risk", "aml", "compliance"]
            stats_keywords = ["count", "average", "total", "how many", "statistics", "data", "analysis"]
            greeting_keywords = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
            help_keywords = ["help", "assist", "support", "guide", "tutorial", "how to"]

            # Extract user ID if present
            user_id_match = re.search(r'\b(?:user\s*id\s*|id\s*)?(\d+)\b', user_input_lower)
            user_id = user_id_match.group(1) if user_id_match else None

            # If input is purely numeric, assume it's a User ID in response to a fraud query
            if user_input.strip().isdigit():
                intent_type = "user_id_response"
                user_id = user_input.strip()
            # Classify intent
            elif any(keyword in user_input_lower for keyword in greeting_keywords):
                intent_type = "greeting"
            elif any(keyword in user_input_lower for keyword in fraud_keywords):
                intent_type = "fraud_analysis"
            elif any(keyword in user_input_lower for keyword in stats_keywords):
                intent_type = "statistics"
            elif any(keyword in user_input_lower for keyword in help_keywords):
                intent_type = "help"
            elif "quit" in user_input_lower or "exit" in user_input_lower or "bye" in user_input_lower:
                intent_type = "exit"
            else:
                intent_type = "general_conversation"

            # Determine specific fraud analysis type
            fraud_subtype = None
            if intent_type == "fraud_analysis":
                if "investigate" in user_input_lower:
                    fraud_subtype = "investigate"
                elif "summary" in user_input_lower or "summarize" in user_input_lower:
                    fraud_subtype = "summary"
                elif "anomaly" in user_input_lower or "anomalous" in user_input_lower or "suspicious" in user_input_lower:
                    fraud_subtype = "risk"
                elif "risk" in user_input_lower or "assessment" in user_input_lower:
                    fraud_subtype = "risk"
                else:
                    fraud_subtype = "investigate"  # Default to investigation

            result = {
                "intent_type": intent_type,
                "fraud_subtype": fraud_subtype,
                "user_id": user_id,
                "confidence": 0.9 if intent_type != "general_conversation" else 0.7,
                "requires_user_id": intent_type == "fraud_analysis" and not user_id
            }

            self.log_interaction("Intent Classification Complete", {"result": result})
            return result

    # --- Transaction Summarization Agent ---
    class TransactionSummarizationAgent(BaseAgent):
        def __init__(self, groq_client: Any):
            super().__init__("Transaction Summarization Agent", groq_client)

        def summarize(self, user_transactions: pd.DataFrame) -> str:
            self.log_interaction("Starting User Summarization", {"user_id": user_transactions['User_ID_str'].iloc[0] if not user_transactions.empty else 'N/A'})
            if user_transactions.empty:
                return "❌ Error: No transaction data found for the user."

            user_id = user_transactions['User_ID_str'].iloc[0]
            total_transactions = len(user_transactions)
            total_amount = user_transactions['TransactionAmt'].sum()
            fraud_count = len(user_transactions[user_transactions['isFraud'] == 1])
            countries = user_transactions['Country'].unique().tolist()
            cross_border_count = len(user_transactions[user_transactions['Is_Cross_Border'] == 1])

            summary_parts = [
                f"📋 User ID: {user_id}",
                f"🔢 Total Transactions: {total_transactions}",
                f"💰 Total Amount: ₹{total_amount:.2f}",
                f"🌍 Countries Involved: {', '.join(countries)}",
                f"🔄 Cross-Border Transactions: {cross_border_count}",
                f"🚨 Fraudulent Transactions: {fraud_count}"
            ]

            result = "\n".join(summary_parts)
            self.log_interaction("Summarization Complete", {"result": "Summary generated successfully"})
            return result

    # --- Risk Assessment Agent ---
    class RiskAssessmentAgent(BaseAgent):
        def __init__(self, groq_client: Any):
            super().__init__("Risk Assessment Agent", groq_client)
            self.risk_thresholds = {"LOW": 30, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 95}

        def calculate_comprehensive_risk_score(self, user_transactions: pd.DataFrame, user_id: str) -> Dict[str, Any]:
            self.log_interaction("Calculating Risk Score", {"user_id": user_id})

            risk_score = 0
            risk_factors = []

            if user_transactions.empty:
                return {
                    "risk_score": 0,
                    "risk_level": "LOW",
                    "risk_factors": ["❌ No transactions found for user"],
                    "requires_document_verification": False,
                    "requires_manual_review": False,
                    "transaction_approved": True
                }

            # Analyze user transactions
            total_amount = user_transactions['TransactionAmt'].sum()
            fraud_count = len(user_transactions[user_transactions['isFraud'] == 1])
            cross_border_count = len(user_transactions[user_transactions['Is_Cross_Border'] == 1])
            high_amount_count = len(user_transactions[user_transactions['TransactionAmt'] > 50000])

            if fraud_count > 0:
                risk_score += 40
                risk_factors.append(f"🚨 {fraud_count} fraudulent transaction(s) detected")

            if total_amount > 100000:
                risk_score += 25
                risk_factors.append(f"💰 High total amount: ₹{total_amount:.2f}")
            elif total_amount > 50000:
                risk_score += 15
                risk_factors.append(f"💰 Moderate total amount: ₹{total_amount:.2f}")

            if cross_border_count > 0:
                risk_score += 20
                risk_factors.append(f"🌍 {cross_border_count} cross-border transaction(s)")

            if high_amount_count > 0:
                risk_score += 10
                risk_factors.append(f"💸 {high_amount_count} high-amount transaction(s) (>₹50,000)")

            risk_score = min(risk_score, 100)
            risk_level = "LOW"
            for level, threshold in sorted(self.risk_thresholds.items(), key=lambda x: x[1]):
                if risk_score >= threshold:
                    risk_level = level

            result = {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors if risk_factors else ["✅ No significant risk factors"],
                "requires_document_verification": risk_score >= 80,
                "requires_manual_review": risk_score >= 60,
                "transaction_approved": risk_score < 80
            }

            self.log_interaction("Risk Assessment Complete", {"risk_score": risk_score, "risk_level": risk_level})
            return result

    # --- Document Verification Agent ---
    class DocumentVerificationAgent(BaseAgent):
        def __init__(self, groq_client: Any):
            super().__init__("Document Verification Agent", groq_client)

        def request_document_verification(self, country: str, user_id: str) -> Tuple[bool, str]:
            print(f"\n🔒 HIGH RISK USER - VERIFICATION REQUIRED 🔒")
            print(f"User ID: {user_id} | Country: {country}")

            if country == "India":
                print("📄 Required: Aadhaar (12 digits) or PAN (10 characters)")
                doc_input = input("Enter Aadhaar number or PAN: ").strip()
                if len(doc_input) == 12 and doc_input.isdigit():
                    return True, f"✅ Aadhaar verified for User {user_id}"
                elif len(doc_input) == 10 and re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', doc_input.upper()):
                    return True, f"✅ PAN verified for User {user_id}"
                else:
                    return False, f"❌ Invalid document format for User {user_id}"

            elif country == "USA":
                print("📄 Required: SSN (XXX-XX-XXXX format)")
                ssn = input("Enter SSN: ").strip()
                if re.match(r'^\d{3}-\d{2}-\d{4}$', ssn):
                    return True, f"✅ SSN verified for User {user_id}"
                else:
                    return False, f"❌ Invalid SSN format for User {user_id}"

            else:
                print("📄 Required: Passport number")
                passport = input("Enter passport number: ").strip()
                if len(passport) >= 6:
                    return True, f"✅ Passport verified for User {user_id}"
                else:
                    return False, f"❌ Invalid passport format for User {user_id}"

    # --- Cross-Border Compliance Agent ---
    class CrossBorderComplianceAgent(BaseAgent):
        def __init__(self, groq_client: Any):
            super().__init__("Cross-Border Compliance Agent", groq_client)

        def process_compliance_check(self, country: str, user_id: str, total_amount: float) -> Tuple[bool, str]:
            print(f"\n🌍 CROSS-BORDER COMPLIANCE CHECK 🌍")
            print(f"User: {user_id} | Country: {country} | Total Amount: ₹{total_amount:.2f}")

            requirements = {
                "India": ["Source of funds declaration", "Tax compliance certificate", "RBI approval"],
                "USA": ["IRS form verification", "OFAC compliance check", "AML clearance"],
                "Other": ["Source verification", "Tax compliance", "Regulatory approval"]
            }

            checklist = requirements.get(country, requirements["Other"])

            print("Required compliance checks:")
            for i, req in enumerate(checklist, 1):
                print(f"{i}. {req}")
                response = input(f"   Confirmed (Y/N): ").strip().upper()
                if response != 'Y':
                    return False, f"❌ Compliance failed: {req} not confirmed"
                print(f"   ✅ Confirmed")

            return True, f"✅ All compliance requirements met for User {user_id}"

    # --- LangChain Conversational Agent ---
    class LangChainConversationalAgent:
        def __init__(self, groq_client: Any, tools: List):
            self.groq_client = groq_client
            self.tools = tools
            self.llm = None
            self.agent_executor = None
            self.runnable_with_history = None
            self.memory = ChatMessageHistory()
            self.pending_user_id_request = False
            self.last_fraud_query = None
            self.last_intent = None

            if groq_client:
                try:
                    self.llm = ChatGroq(
                        temperature=0.7,
                        model_name="llama3-8b-8192",
                        groq_api_key=os.getenv("GROQ_API_KEY"))

                    self.prompt = ChatPromptTemplate.from_messages([
                        ("system", """You are an intelligent, friendly AI assistant specializing in fraud detection and AML compliance.
                        You can engage in natural conversations about any topic while being most helpful with financial security matters.

                        Your capabilities include:
                        - Fraud transaction analysis and investigation
                        - Risk assessment and anomaly detection
                        - Document verification and compliance checking
                        - General conversation and assistance
                        - Statistical analysis of transaction data

                        For fraud-related queries (e.g., checking if transactions are suspicious, investigating fraud, or assessing risk), you MUST:
                        1. Identify if a User ID is provided in the input.
                        2. If no User ID is provided, respond with a polite request for the User ID and nothing else.
                        3. If a User ID is provided, use the available tools to fetch all transaction details automatically and proceed with the requested analysis.
                        4. Do NOT ask for additional details like transaction type, amount, date, or account information.

                        Always be helpful, conversational, and use emojis appropriately.
                        If the query is unrelated to fraud detection, be helpful and engaging, and gently mention your specialty in fraud detection.

                        Available tools: {tool_names}
                        Today's date: May 29, 2025
                        """),
                        MessagesPlaceholder(variable_name="chat_history"),
                        ("human", "{input}"),
                        MessagesPlaceholder(variable_name="agent_scratchpad")
                    ])

                    agent = create_tool_calling_agent(self.llm, self.tools, prompt=self.prompt)
                    self.agent_executor = AgentExecutor(
                        agent=agent,
                        tools=self.tools,
                        verbose=True,
                        handle_parsing_errors=True,
                        max_iterations=2)

                    self.runnable_with_history = RunnableWithMessageHistory(
                        runnable=self.agent_executor,
                        get_session_history=lambda x: self.memory,
                        input_messages_key="input",
                        history_messages_key="chat_history")

                    print("✅ Advanced conversational AI agent initialized successfully!")
                except Exception as e:
                    print(f"ERROR: Advanced conversational AI agent initialization failed: {e}")
                    self.runnable_with_history = None
            else:
                self.runnable_with_history = None

        def get_ai_response(self, user_input: str, outer_instance: 'Fraud_AML_Agent') -> str:
            try:
                intent_analysis = outer_instance.intent_classifier.classify_user_intent(user_input)
                is_fraud_related = intent_analysis["intent_type"] == "fraud_analysis" or intent_analysis["intent_type"] == "user_id_response"
                user_id = intent_analysis["user_id"]

                if self.pending_user_id_request and (intent_analysis["intent_type"] == "user_id_response" or user_input.isdigit()):
                    user_id = user_id if user_id else user_input.strip()
                    if not user_id.isdigit():
                        return "❌ Please enter a valid numeric User ID."
                    intent_analysis = self.last_intent
                    user_input = self.last_fraud_query
                    self.pending_user_id_request = False
                    self.last_fraud_query = None
                    self.last_intent = None
                    is_fraud_related = True
                elif is_fraud_related and not user_id:
                    self.last_fraud_query = user_input
                    self.last_intent = intent_analysis
                    self.pending_user_id_request = True
                    return "📋 Please provide your User ID so I can analyze your transactions."

                if is_fraud_related and user_id:
                    print(f"\n🔍 Analyzing transactions for User {user_id}...")
                    user_transactions = outer_instance.get_user_transactions_by_id(user_id)
                    if user_transactions.empty:
                        self.pending_user_id_request = False
                        self.last_fraud_query = None
                        self.last_intent = None
                        return f"❌ No transactions found for User ID {user_id}. Please try a different User ID or ask me something else."

                    fraud_subtype = intent_analysis.get("fraud_subtype", "investigate")
                    if fraud_subtype == "summary":
                        return outer_instance.transaction_summarization_agent.summarize(user_transactions)
                    elif fraud_subtype == "risk":
                        return outer_instance._detect_anomalies(user_transactions, user_id)
                    else:
                        return outer_instance._conduct_investigation(user_transactions, user_id)

                if self.runnable_with_history:
                    response = self.runnable_with_history.invoke(
                        {"input": user_input, "tool_names": [tool.name for tool in self.tools]},
                        config={"configurable": {"session_id": "main_session"}})
                    return response.get('output', 'I apologize, but I had trouble processing that request.')
                else:
                    return outer_instance.conversational_agent.handle_general_conversation(user_input)

            except Exception as e:
                print(f"AI Agent Error: {e}")
                self.pending_user_id_request = False
                return f"Error processing request: {e}\nPlease try again or ask something else."

    # --- Helper Functions ---
    def get_user_transactions_by_id(self, user_id: str) -> pd.DataFrame:
        if self.df is None:
            return pd.DataFrame()

        try:
            user_id_str = str(user_id)
            user_transactions = self.df[self.df['User_ID_str'] == user_id_str]
            if not user_transactions.empty:
                return user_transactions
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def get_user_input_user_id(self) -> Optional[str]:
        while True:
            user_id = input("\n📋 Please enter your User ID to analyze your transactions: ").strip()
            if user_id.lower() in ['back', 'cancel']:
                return None
            if user_id.isdigit():
                return user_id
            print("❌ Please enter a valid numeric User ID (or 'back' to cancel)")

    def handle_statistical_queries(self, user_input: str) -> str:
        if self.df is None:
            return "❌ Error: Dataset not loaded."

        user_input_lower = user_input.lower()
        months_match = re.search(r'\blast\s*(\d+)\s*months?\b', user_input_lower)

        if "fraud count" in user_input_lower or "how many fraud" in user_input_lower:
            if months_match:
                months_back = int(months_match.group(1))
                end_date = pd.to_datetime("2025-05-29")
                start_date = end_date - pd.offsets.MonthBegin(months_back)
                filtered_df = self.df[
                    (pd.to_datetime(self.df['TransactionDT'], format='%d-%m-%Y %H:%M', errors='coerce') >= start_date) &
                    (pd.to_datetime(self.df['TransactionDT'], format='%d-%m-%Y %H:%M', errors='coerce') <= end_date) &
                    (self.df['isFraud'] == 1)
                ].dropna(subset=['TransactionDT'])
                return f"📊 Found {len(filtered_df)} fraudulent transactions in the last {months_back} months."
            else:
                total_fraud = len(self.df[self.df['isFraud'] == 1])
                return f"📊 Total fraudulent transactions in dataset: {total_fraud}"

        elif "average amount" in user_input_lower:
            if months_match:
                months_back = int(months_match.group(1))
                end_date = pd.to_datetime("2025-05-29")
                start_date = end_date - pd.offsets.MonthBegin(months_back)
                filtered_df = self.df[
                    (pd.to_datetime(self.df['TransactionDT'], format='%d-%m-%Y %H:%M', errors='coerce') >= start_date) &
                    (pd.to_datetime(self.df['TransactionDT'], format='%d-%m-%Y %H:%M', errors='coerce') <= end_date)
                ].dropna(subset=['TransactionDT'])
                if filtered_df.empty:
                    return f"📊 No transactions found in the last {months_back} months."
                return f"📊 Average transaction amount (last {months_back} months): ₹{filtered_df['TransactionAmt'].mean():.2f}"
            else:
                return f"📊 Overall average transaction amount: ₹{self.df['TransactionAmt'].mean():.2f}"

        return "❌ I didn't understand that statistical query. Try asking about 'fraud count' or 'average amount'."

    # --- Tool Functions for LangChain ---
    def get_user_transactions_tool(self, user_id: str) -> str:
        user_transactions = self.get_user_transactions_by_id(user_id)
        if user_transactions.empty:
            return json.dumps(user_transactions.to_dict('records'), default=str)
        return f"Error: No transactions found for User ID {user_id}"

    def summarize_user_tool(self, user_id: str) -> str:
        user_transactions = self.get_user_transactions_by_id(user_id)
        if user_transactions.empty:
            return f"Error: No transactions found for User ID {user_id}"
        return self.transaction_summarization_agent.summarize(user_transactions)

    def assess_user_risk_tool(self, user_id: str) -> str:
        user_transactions = self.get_user_transactions_by_id(user_id)
        if user_transactions.empty:
            return f"Error: No transactions found for User ID {user_id}"
        risk_assessment = self.risk_assessment_agent.calculate_comprehensive_risk_score(user_transactions, user_id)
        return f"Risk Score: {risk_assessment['risk_score']}/100, Level: {risk_assessment['risk_level']}, Factors: {', '.join(risk_assessment['risk_factors'])}"

    def get_fraud_statistics_tool(self, query: str) -> str:
        return self.handle_statistical_queries(query)

    def _create_langchain_tools(self) -> List:
        return [
            Tool(
                name="get_user_transactions",
                func=self.get_user_transactions_tool,
                description="Retrieve all transaction details for a specific user by User ID. Use this to fetch data for fraud analysis, risk assessment, or transaction summaries."
            ),
            Tool(
                name="summarize_user",
                func=self.summarize_user_tool,
                description="Generate a summary of a user's transactions based on the provided User ID."
            ),
            Tool(
                name="assess_user_risk",
                func=self.assess_user_risk_tool,
                description="Assess the risk level of a user's transactions based on the provided User ID."
            ),
            Tool(
                name="get_fraud_statistics",
                func=self.get_fraud_statistics_tool,
                description="Retrieve statistics about fraud transactions from the dataset, such as fraud counts or average transaction amounts."
            )
        ]

    # --- Orchestrator Logic ---
    def log_interaction(self, action: str, details: Dict[str, Any]) -> None:
        print(f"[Agent: Fraud_AML_Agent] {action}: {details}")

    def process_user_input(self, user_input: str) -> str:
        self.conversation_history.append({"user": user_input, "timestamp": datetime.now()})
        greeting_response = self.conversational_agent.respond_to_greeting(user_input)
        if greeting_response:
            return greeting_response

        intent_analysis = self.intent_classifier.classify_user_intent(user_input)
        self.log_interaction("Processing User Input", {
            "intent": intent_analysis["intent_type"],
            "confidence": intent_analysis["confidence"]
        })

        if intent_analysis["intent_type"] == "greeting":
            return self.conversational_agent.respond_to_greeting(user_input)
        elif intent_analysis["intent_type"] == "help":
            return self._provide_help()
        elif intent_analysis["intent_type"] == "exit":
            return "👋 Thank you for using the Fraud Detection System! Stay safe and secure. Goodbye!"
        elif intent_analysis["intent_type"] == "statistics":
            return self.handle_statistical_queries(user_input)
        elif intent_analysis["intent_type"] == "fraud_analysis":
            user_id = intent_analysis.get("user_id")
            if not user_id:
                user_id = self.get_user_input_user_id()
                if not user_id:
                    return "Operation cancelled. Feel free to ask me anything else!"

            print(f"\n🔍 Analyzing transactions for User {user_id}...")
            user_transactions = self.get_user_transactions_by_id(user_id)
            if user_transactions.empty:
                return f"❌ No transactions found for User ID {user_id}. Please try a different User ID or ask me something else!"

            fraud_subtype = intent_analysis.get("fraud_subtype", "investigate")
            if fraud_subtype == "summary":
                return self._generate_summary(user_transactions)
            elif fraud_subtype == "risk":
                return self._detect_anomalies(user_transactions, user_id)
            else:
                return self._conduct_investigation(user_transactions, user_id)
        elif intent_analysis["intent_type"] == "general_conversation":
            return self.conversational_agent.handle_general_conversation(user_input)

        return "🤔 I'm not sure how to help with that. Could you please rephrase or ask me something else?"

    def _provide_help(self) -> str:
        help_text = """
🆘 **HELP - What I Can Do For You** 🆘

🛡️ **Fraud Detection & Analysis:**
• "investigate user 123" - Full fraud investigation for a user
• "summarize user 456" - User transaction summary
• "analyze risk for user 789" - Risk assessment for a user
• "check if my transactions are suspicious" - Anomaly detection for a user

📊 **Statistics & Data Analysis:**
• "fraud count last 3 months" - Count fraudulent transactions
• "average transaction amount" - Calculate averages
• "how many fraud transactions" - Overall fraud statistics

💬 **General Conversation:**
• Ask me anything! I can chat about various topics
• Get information about cybersecurity, finance, or general questions
• I'm here to help with both professional and casual conversations

🌟 **Special Features:**
• Smart document verification for high-risk users
• Cross-border compliance checking
• Real-time risk assessment with detailed reports

Just type your question naturally - for fraud-related queries, I'll only need your User ID to fetch all transaction details!
        """
        return help_text

    def _generate_summary(self, user_transactions: pd.DataFrame) -> str:
        print("📊 Generating user transaction summary...")
        summary = self.transaction_summarization_agent.summarize(user_transactions)
        return f"📋 **USER TRANSACTION SUMMARY**\n\n{summary}"

    def _detect_anomalies(self, user_transactions: pd.DataFrame, user_id: str) -> str:
        print("🔍 Detecting anomalies...")
        risk_assessment = self.risk_assessment_agent.calculate_comprehensive_risk_score(user_transactions, user_id)

        result = f"""🚨 **ANOMALY DETECTION REPORT**

🎯 **Risk Assessment:**
• Risk Score: {risk_assessment['risk_score']}/100
• Risk Level: {risk_assessment['risk_level']}
• Status: {'⚠️ ATTENTION REQUIRED' if not risk_assessment['transaction_approved'] else '✅ APPROVED'}

🔍 **Detected Issues:**
"""
        for factor in risk_assessment['risk_factors']:
            result += f"• {factor}\n"

        return result

    def _assess_risk(self, user_transactions: pd.DataFrame, user_id: str) -> str:
        print("⚖️ Conducting risk assessment...")
        risk_assessment = self.risk_assessment_agent.calculate_comprehensive_risk_score(user_transactions, user_id)

        result = f"""⚖️ **COMPREHENSIVE RISK ASSESSMENT**

📊 **Risk Metrics:**
• Score: {risk_assessment['risk_score']}/100
• Level: {risk_assessment['risk_level']}
• Document Verification: {'Required' if risk_assessment['requires_document_verification'] else 'Not Required'}
• Manual Review: {'Required' if risk_assessment['requires_manual_review'] else 'Not Required'}

🔍 **Risk Factors:**
"""
        for factor in risk_assessment['risk_factors']:
            result += f"• {factor}\n"

        return result

    def _conduct_investigation(self, user_transactions: pd.DataFrame, user_id: str) -> str:
        print("🕵️‍♂️ Conducting comprehensive investigation...")
        country = user_transactions['Country'].iloc[0] if not user_transactions.empty else 'Unknown'
        total_amount = user_transactions['TransactionAmt'].sum() if not user_transactions.empty else 0
        cross_border_count = len(user_transactions[user_transactions['Is_Cross_Border'] == 1]) if not user_transactions.empty else 0

        results = []
        print("📊 Step 1: User transaction summary...")
        summary = self.transaction_summarization_agent.summarize(user_transactions)
        results.append(f"📋 **USER TRANSACTION SUMMARY**\n{summary}\n")

        print("⚖️ Step 2: Risk assessment...")
        risk_assessment = self.risk_assessment_agent.calculate_comprehensive_risk_score(user_transactions, user_id)
        risk_report = f"""⚖️ **RISK ASSESSMENT**
• Risk Score: {risk_assessment['risk_score']}/100
• Level: {risk_assessment['risk_level']}

🔍 **Risk Factors:**
"""
        for factor in risk_assessment['risk_factors']:
            risk_report += f"• {factor}\n"
        results.append(risk_report)

        if risk_assessment['requires_document_verification']:
            print("🔒 Step 3: Document verification...")
            doc_verified, doc_msg = self.document_verification_agent.request_document_verification(country, user_id)
            results.append(f"📄 **DOCUMENT VERIFICATION**\n{doc_msg}\n")
            if not doc_verified:
                results.append(f"❌ **FINAL DECISION:** User {user_id} transactions REJECTED")
                return "\n".join(results)

        if cross_border_count > 0:
            print("🌍 Step 4: Cross-border compliance...")
            compliance_ok, compliance_msg = self.cross_border_compliance_agent.process_compliance_check(country, user_id, total_amount)
            results.append(f"🌍 **CROSS-BORDER COMPLIANCE**\n{compliance_msg}\n")
            if not compliance_ok:
                results.append(f"❌ **FINAL DECISION:** User {user_id} transactions REJECTED")
                return "\n".join(results)

        if risk_assessment['transaction_approved']:
            final_decision = f"✅ **FINAL DECISION:** User {user_id} transactions APPROVED"
        else:
            final_decision = f"⚠️ **FINAL DECISION:** User {user_id} transactions REQUIRE MANUAL REVIEW"
        results.append(final_decision)
        return "\n\n".join(results)

    def run(self):
        print("=" * 80)
        print("🤖 INTELLIGENT FRAUD DETECTION & CONVERSATIONAL AI SYSTEM 🤖")
        print("=" * 80)
        print("📅 System Date: May 30, 2025, 07:15 AM IST")
        print("🚀 Enhanced with Natural Language Understanding")
        print()

        if self.client:
            print("✅ AI-Powered Conversation: Fully Operational")
            print("🧠 Advanced Language Model: Ready")
        else:
            print("⚠️ WARNING: GROQ_API_KEY not set. Using rule-based responses.")

        print("\n💬 **I can help you with:**")
        print("• Fraud detection and user transaction analysis")
        print("• Risk assessment and anomaly detection")
        print("• Statistical queries about transaction data")
        print("• General conversation and questions")
        print("• Document verification and compliance")
        print("• And much more! Just ask me naturally.")

        print(f"\n📊 Dataset: {self.df.shape[0] if self.df is not None else 0} transactions loaded")
        print("\n🗣️ **Just type what you want to know - I understand natural language!**")
        print("Examples: 'Hello', 'Investigate user 123', 'How are you?', 'Check if my transactions are suspicious', 'Fraud count last month'")
        print("\n" + "=" * 80)

        while True:
            try:
                user_input = input("\nGoal: ").strip()
                if not user_input:
                    print("🤔 I'm listening! Please say something.")
                    continue

                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    print("\nAI: 🤖 👋 It was great talking with you! Stay safe and secure. Goodbye!")
                    break

                print(f"\n🤖 AI: ", end="", flush=True)
                response = None
                if self.advanced_ai.runnable_with_history:
                    response = self.advanced_ai.get_ai_response(user_input, self)
                if not response:
                    response = self.process_user_input(user_input)
                print(response)

            except KeyboardInterrupt:
                print("\n\n🤖 AI: 👋 Thanks for using the system! Goodbye!")
                break
            except Exception as e:
                print(f"\n🤖 AI: 😅 Oops! I encountered an error: {e}")
                print("But I'm still here to help! Please try asking something else.")
    def process_single_query(self, user_input: str) -> str:
        """
        Process a single query without entering interactive mode.
        This method is used for integration with the main orchestrator.
        """
        try:
            # Use the advanced AI response if available
            if self.advanced_ai.runnable_with_history:
                response = self.advanced_ai.get_ai_response(user_input, self)
            else:
                response = self.process_user_input(user_input)
            
            return response
            
        except Exception as e:
            return f"Error processing fraud detection query: {str(e)}"
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get the current status of the fraud detection agent."""
        return {
            "agent_type": "Fraud_Detection_AML",
            "dataset_loaded": self.df is not None,
            "dataset_size": len(self.df) if self.df is not None else 0,
            "groq_client_available": self.client is not None,
            "advanced_ai_available": self.advanced_ai.runnable_with_history is not None,
            "status": "operational"
        }
if __name__ == "__main__":
    agent = Fraud_AML_Agent()
    agent.run()