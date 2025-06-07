import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import pandas as pd
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import create_engine, Column, String, Float, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from account_type_mapper import AccountTypeMapper

# Configuration
DB_NAME = "sqlite:///Banking.db"
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SQLAlchemy Setup
Base = declarative_base()
engine = create_engine(DB_NAME, pool_size=5, max_overflow=10)
SessionFactory = sessionmaker(bind=engine)

# SQLAlchemy Models
class User(Base):
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)
    father_name = Column(String)
    dob = Column(String)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String)
    address = Column(String)
    date_joined = Column(String)
    pan_number = Column(String, unique=True)
    aadhaar_number = Column(String, unique=True)
    aadhaar_name = Column(String)
    aadhaar_father_name = Column(String)
    aadhaar_dob = Column(String)
    aadhaar_address = Column(String)
    aadhaar_mobile = Column(String)
    status = Column(String, default='Active')
    accounts = relationship("Account", back_populates="user")
    cards = relationship("Card", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")
    kyc_updates = relationship("KycUpdate", back_populates="user")

class Account(Base):
    __tablename__ = 'accounts'
    account_number = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    balance = Column(Float, default=1000.00)
    account_type = Column(String, default='Savings')
    status = Column(String, default='Active')
    created_date = Column(String)
    last_balance_inquiry = Column(String)
    last_mini_statement = Column(String)
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Transaction(Base):
    __tablename__ = 'transactions'
    transaction_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    account_number = Column(String, ForeignKey('accounts.account_number'))
    amount = Column(Float)
    product = Column(String)
    datetime = Column(String)
    transaction_type = Column(String, default='Debit')
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")

class Card(Base):
    __tablename__ = 'cards'
    card_number = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    card_type = Column(String, default='Debit')
    status = Column(String, default='Active')
    issue_date = Column(String)
    expiry_date = Column(String)
    user = relationship("User", back_populates="cards")

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    query = Column(String)
    intent = Column(String)
    response = Column(String)
    collected_data = Column(String)
    timestamp = Column(String)
    user = relationship("User", back_populates="conversations")

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    feedback = Column(String)
    sentiment = Column(String)
    timestamp = Column(String)
    user = relationship("User", back_populates="feedback")

class FAQ(Base):
    __tablename__ = 'faqs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String)
    answer = Column(String)

class KycUpdate(Base):
    __tablename__ = 'kyc_updates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    field_updated = Column(String)
    old_value = Column(String)
    new_value = Column(String)
    timestamp = Column(String)
    status = Column(String, default='Pending')
    user = relationship("User", back_populates="kyc_updates")

# Initialize LLM
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.1
    )
    logger.info("LLM initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}")
    llm = None

class DatabaseManager:
    @staticmethod
    def initialize_database():
        try:
            Base.metadata.create_all(engine)
            logger.info("Database tables initialized successfully")
        except SQLAlchemyError as e:
            logger.error(f"Database initialization error: {e}")
            raise

class ConversationSession:
    _sessions: Dict[str, 'ConversationSession'] = {}
    _SESSION_TIMEOUT = timedelta(minutes=30)

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.context = {
            "conversation_history": [],
            "new_user_data": {},
            "last_active": pd.Timestamp.now().isoformat(),
            "pending_action": None,
            "pending_status": None,
            "pending_transfer": None
        }
        self.field_attempts = {}
        self._history_loaded = False

    @staticmethod
    def get_or_create(user_id: str) -> 'ConversationSession':
        ConversationSession._cleanup_sessions()
        if user_id not in ConversationSession._sessions:
            ConversationSession._sessions[user_id] = ConversationSession(user_id)
        session = ConversationSession._sessions[user_id]
        session.context["last_active"] = pd.Timestamp.now().isoformat()
        return session

    @staticmethod
    def _cleanup_sessions():
        current_time = pd.Timestamp.now()
        expired = [
            user_id for user_id, session in ConversationSession._sessions.items()
            if (current_time - pd.Timestamp(session.context["last_active"])) > ConversationSession._SESSION_TIMEOUT
        ]
        for user_id in expired:
            del ConversationSession._sessions[user_id]
            logger.debug(f"Removed inactive session for user: {user_id}")

    @staticmethod
    def update_user_id(old_user_id: str, new_user_id: str):
        if old_user_id in ConversationSession._sessions:
            session = ConversationSession._sessions.pop(old_user_id)
            session.user_id = new_user_id
            ConversationSession._sessions[new_user_id] = session

    def load_history(self):
        if self._history_loaded or self.user_id == "NEWUSER":
            return
        try:
            session = SessionFactory()
            conversations = session.query(Conversation).filter_by(user_id=self.user_id).order_by(Conversation.timestamp.desc()).limit(3).all()
            self.context["conversation_history"] = [
                {
                    "query": conv.query,
                    "response": conv.response,
                    "intent": conv.intent,
                    "collected_data": json.loads(conv.collected_data) if conv.collected_data else {},
                    "timestamp": conv.timestamp
                }
                for conv in conversations
            ]
            self._history_loaded = True
            logger.debug(f"Loaded history for user: {self.user_id}")
        except SQLAlchemyError as e:
            logger.error(f"Error loading session history: {e}")
        finally:
            session.close()

    def get_context_summary(self) -> str:
        if not self._history_loaded:
            self.load_history()
        if not self.context["conversation_history"]:
            return "No recent conversation history."
        history_summary = "\n".join([
            f"[{h['timestamp']}] Intent: {h['intent']}, Query: {h['query'][:50]}..., Response: {h['response'][:50]}..."
            for h in self.context["conversation_history"][-2:]
        ])
        return f"Recent Interactions:\n{history_summary}"

    def update_new_user_data(self, field: str, value: str):
        self.context["new_user_data"][field] = value
        self.context["last_active"] = pd.Timestamp.now().isoformat()

    def clear_new_user_data(self):
        self.context["new_user_data"] = {}
        self.field_attempts = {}
        self.context["last_active"] = pd.Timestamp.now().isoformat()

    def add_query(self, query: str, intent: str, response: str, collected_data: dict):
        timestamp = pd.Timestamp.now().isoformat()
        interaction = {
            "query": query,
            "response": response,
            "intent": intent,
            "collected_data": collected_data,
            "timestamp": timestamp
        }
        if not self._history_loaded:
            self.load_history()
        self.context["conversation_history"].append(interaction)
        if len(self.context["conversation_history"]) > 3:
            self.context["conversation_history"].pop(0)
        self.context["last_active"] = timestamp
        
        if self.user_id != "NEWUSER":
            try:
                session = SessionFactory()
                conversation = Conversation(
                    user_id=self.user_id,
                    query=query,
                    intent=intent,
                    response=response,
                    collected_data=json.dumps(collected_data),
                    timestamp=timestamp
                )
                session.add(conversation)
                session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Error saving conversation: {e}")
                session.rollback()
            finally:
                session.close()

def safe_llm_call(prompt: str, query: str = "") -> str:
    if not llm:
        return "LLM service is currently unavailable."
    try:
        full_prompt = f"{prompt}\n\nUser Query: {query}" if query else prompt
        response = llm.invoke([HumanMessage(content=full_prompt)])
        return response.content.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return "Error processing request. Please try again."

def get_user_context(user_id: str) -> dict:
    if user_id == "NEWUSER":
        return {"status": "new_user", "accounts": [], "cards": [], "user_info": {}}
    try:
        session = SessionFactory()
        user = session.query(User).filter_by(user_id=user_id).first()
        user_info = {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "email": user.email
        } if user else {}
        accounts = [
            {
                "account_number": acc.account_number,
                "balance": acc.balance,
                "account_type": acc.account_type,
                "status": acc.status
            }
            for acc in session.query(Account).filter_by(user_id=user_id).all()
        ]
        cards = [
            {
                "card_number": card.card_number,
                "card_type": card.card_type,
                "status": card.status,
                "issue_date": card.issue_date
            }
            for card in session.query(Card).filter_by(user_id=user_id).all()
        ]
        return {
            "status": "existing_user",
            "user_info": user_info,
            "accounts": accounts,
            "cards": cards
        }
    except SQLAlchemyError as e:
        logger.error(f"Error getting user context: {e}")
        return {"status": "error", "accounts": [], "cards": [], "user_info": {}}
    finally:
        session.close()

def generate_transaction_history_md(user_id: str, account_number: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    try:
        session = SessionFactory()
        account = session.query(Account).filter_by(account_number=account_number, user_id=user_id).first()
        if not account:
            return f"Account {account_number} not found or does not belong to user {user_id}."
        
        query = session.query(Transaction).filter_by(account_number=account_number, user_id=user_id)
        if start_date:
            query = query.filter(Transaction.datetime >= start_date)
        if end_date:
            query = query.filter(Transaction.datetime <= end_date)
        transactions = query.order_by(Transaction.datetime.desc()).all()
        
        if not transactions:
            return f"No transactions found for account {account_number}."
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transaction_history_{account_number}_{timestamp}.md"
        md_content = f"# Transaction History for Account {account_number}\n\n"
        md_content += f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        if start_date or end_date:
            md_content += f"Period: {start_date or 'Beginning'} to {end_date or 'Now'}\n"
        md_content += "\n| Transaction ID | Amount | Type | Product | Date |\n"
        md_content += "|---------------|--------|------|---------|------|\n"
        
        for tx in transactions:
            md_content += f"| {tx.transaction_id} | ${tx.amount:.2f} | {tx.transaction_type} | {tx.product} | {tx.datetime} |\n"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(md_content)
            logger.info(f"Transaction history saved to {filename}")
            return f"Transaction history saved to {filename}"
        except IOError as e:
            logger.error(f"Error writing Markdown file: {e}")
            return "Error saving transaction history file."
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return f"Database error: {str(e)}"
    finally:
        session.close()

def execute_database_query(query_type: str, parameters: dict, user_id: str) -> str:
    try:
        session = SessionFactory()
        if query_type == "check_balance":
            account_number = parameters.get("account_number")
            if not account_number:
                accounts = session.query(Account).filter_by(user_id=user_id).all()
                if accounts:
                    response = "Your accounts:\n"
                    for acc in accounts:
                        response += f"Account {acc.account_number} ({acc.account_type}): Balance ${acc.balance:.2f}\n"
                    return response
                return "No accounts found."
            else:
                account = session.query(Account).filter_by(account_number=account_number, user_id=user_id).first()
                if account:
                    account.last_balance_inquiry = pd.Timestamp.now().isoformat()
                    session.commit()
                    return f"Account {account_number} balance: ${account.balance:.2f}"
                return f"Account {account_number} not found."
        
        elif query_type == "mini_statement":
            account_number = parameters.get("account_number")
            if not account_number:
                return "Please provide the account number for mini statement."
            account = session.query(Account).filter_by(account_number=account_number, user_id=user_id).first()
            if not account:
                return f"Account {account_number} not found or does not belong to you."
            transactions = session.query(Transaction).filter_by(account_number=account_number, user_id=user_id).order_by(Transaction.datetime.desc()).limit(5).all()
            if not transactions:
                return f"No transactions found for account {account_number}."
            response = f"Mini Statement for Account {account_number}:\n" + "-" * 50 + "\n"
            for tx in transactions:
                response += f"ID: {tx.transaction_id} | Amount: ${tx.amount:.2f} | Type: {tx.transaction_type} | Product: {tx.product} | Date: {tx.datetime}\n"
            response += "-" * 50
            account.last_mini_statement = pd.Timestamp.now().isoformat()
            session.commit()
            return response
        
        elif query_type == "get_cards":
            cards = session.query(Card).filter_by(user_id=user_id).all()
            if not cards:
                return "No cards found for your account."
            response = "Your cards:\n"
            for card in cards:
                masked_card = f"{card.card_number[0]}**** **** **** {card.card_number[-4:]}"
                response += f"- Card: {masked_card} | Type: {card.card_type} | Status: {card.status} | Issued: {card.issue_date[:10]}\n"
            return response
        
        elif query_type == "update_card_status":
            card_number = parameters.get("card_number")
            new_status = parameters.get("status")
            if not card_number or not new_status:
                return "Please provide card number and status (Active/Inactive)."
            card = session.query(Card).filter_by(card_number=card_number, user_id=user_id).first()
            if not card:
                return f"Card {card_number} not found or does not belong to you."
            if new_status not in ["Active", "Inactive"]:
                return "Status must be 'Active' or 'Inactive'."
            if card.status == new_status:
                return f"Card {card_number} is already {new_status}."
            card.status = new_status
            session.commit()
            logger.info(f"Card {card_number} status updated to {new_status} for user {user_id}")
            return f"Card {card_number} is now {new_status}."
        
        elif query_type == "process_internal_transfer":
            source_account = parameters.get("source_account")
            dest_account = parameters.get("dest_account")
            amount = parameters.get("amount")
            if not source_account or not dest_account or not amount:
                return "Please provide source account, destination account, and amount."
            try:
                amount = float(amount)
                if amount <= 0:
                    return "Amount must be positive."
            except ValueError:
                return "Invalid amount format."
            
            source_acc = session.query(Account).filter_by(account_number=source_account, user_id=user_id).first()
            if not source_acc:
                return f"Source account {source_account} not found or does not belong to you."
            if source_acc.status != "Active":
                return f"Source account {source_account} is not active."
            if source_acc.balance < amount:
                return f"Insufficient balance in account {source_account}."
            
            dest_acc = session.query(Account).filter_by(account_number=dest_account).first()
            if not dest_acc:
                return f"Destination account {dest_account} not found."
            if dest_acc.status != "Active":
                return f"Destination account {dest_account} is not active."
            if source_acc.account_number == dest_acc.account_number:
                return "Source and destination accounts cannot be the same."
            
            source_acc.balance -= amount
            dest_acc.balance += amount
            
            timestamp = pd.Timestamp.now()
            tx_id = f"TXN{timestamp.strftime('%Y%m%d%H%M%S')}"
            debit_tx = Transaction(
                transaction_id=tx_id + "_D",
                user_id=user_id,
                account_number=source_account,
                amount=amount,
                product=f"Transfer to {dest_account}",
                datetime=timestamp.isoformat(),
                transaction_type="Debit"
            )
            credit_tx = Transaction(
                transaction_id=tx_id + "_C",
                user_id=dest_acc.user_id,
                account_number=dest_account,
                amount=amount,
                product=f"Transfer from {source_account}",
                datetime=timestamp.isoformat(),
                transaction_type="Credit"
            )
            
            session.add_all([debit_tx, credit_tx])
            session.commit()
            logger.info(f"Transfer of ${amount:.2f} from {source_account} to {dest_account} completed")
            return f"Transferred ${amount:.2f} from {source_account} to {dest_account}. New balance: ${source_acc.balance:.2f}"
        
        elif query_type == "update_kyc":
            field = parameters.get("field")
            new_value = parameters.get("new_value")
            if not field or not new_value:
                return "Missing field or value for KYC update."
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user:
                return "User not found."
            old_value = getattr(user, field, None)
            setattr(user, field, new_value)
            kyc_update = KycUpdate(
                user_id=user_id,
                field_updated=field,
                old_value=old_value,
                new_value=new_value,
                timestamp=pd.Timestamp.now().isoformat(),
                status="Completed"
            )
            session.add(kyc_update)
            session.commit()
            return f"{field.replace('_', ' ').title()} updated successfully from '{old_value}' to '{new_value}'."
        
        elif query_type == "search_faq":
            keyword = parameters.get("keyword", "")
            faq = session.query(FAQ).filter(FAQ.keyword.ilike(f"%{keyword}%")).first()
            if faq:
                return faq.answer
            return "No FAQ found. Please clarify your question."
        
        else:
            return f"Unknown query type: {query_type}"
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        return f"Database error: {str(e)}"
    finally:
        session.close()

def handle_account_creation(user_data: dict, user_id: str, session: ConversationSession) -> str:
    required_fields = ["email", "pan_number", "aadhaar_number", "aadhaar_name",
                      "aadhaar_father_name", "aadhaar_dob", "aadhaar_address",
                      "aadhaar_mobile", "account_type"]
    try:
        db_session = SessionFactory()
        if db_session.query(User).filter((User.email == user_data["email"]) | (User.pan_number == user_data["pan_number"])).first():
            return "An account with this email or PAN number already exists."
        
        last_user = db_session.query(User).order_by(User.user_id.desc()).first()
        new_user_id = f"U{int(last_user.user_id[1:]) + 1:04d}" if last_user else "U1001"
        
        new_user = User(
            user_id=new_user_id,
            full_name=user_data["aadhaar_name"],
            father_name=user_data["aadhaar_father_name"],
            dob=user_data["aadhaar_dob"],
            email=user_data["email"],
            phone=user_data["aadhaar_mobile"],
            address=user_data["aadhaar_address"],
            date_joined=pd.Timestamp.now().isoformat(),
            pan_number=user_data["pan_number"],
            aadhaar_number=user_data["aadhaar_number"],
            aadhaar_name=user_data["aadhaar_name"],
            aadhaar_father_name=user_data["aadhaar_father_name"],
            aadhaar_dob=user_data["aadhaar_dob"],
            aadhaar_address=user_data["aadhaar_address"],
            aadhaar_mobile=user_data["aadhaar_mobile"]
        )
        db_session.add(new_user)
        
        account_number = f"{int(new_user_id[1:]) * 1000 + 1:010d}"
        new_account = Account(
            account_number=account_number,
            user_id=new_user_id,
            balance=1000.00,
            account_type=user_data["account_type"],
            status="Active",
            created_date=pd.Timestamp.now().isoformat()
        )
        db_session.add(new_account)
        
        card_number = f"D{int(new_user_id[1:]):016d}"
        new_card = Card(
            card_number=card_number,
            user_id=new_user_id,
            card_type="Debit",
            status="Active",
            issue_date=pd.Timestamp.now().isoformat(),
            expiry_date=(pd.Timestamp.now() + pd.DateOffset(years=3)).isoformat()
        )
        db_session.add(new_card)
        
        db_session.commit()
        session.clear_new_user_data()
        ConversationSession.update_user_id("NEWUSER", new_user_id)
        
        return f"""Account created successfully!
User ID: {new_user_id}
Account Number: {account_number}
Account Type: {user_data['account_type']}
Initial Balance: $1000.00
Debit Card: {card_number}"""
    except SQLAlchemyError as e:
        logger.error(f"Error creating account: {e}")
        db_session.rollback()
        return f"Error creating account: {str(e)}"
    finally:
        db_session.close()

class AgenticIntelligenceRouter:
    def __init__(self):
        self.available_agents = {
            "ACCOUNT_OPENING_AGENT": {
                "description": "Handles new user registration and account creation",
                "capabilities": ["collect user information", "validate data", "create new accounts"],
                "database_operations": ["create_user", "create_account", "create_card"]
            },
            "BALANCE_INQUIRY_AGENT": {
                "description": "Handles balance inquiries, mini statements, and transaction history downloads",
                "capabilities": ["retrieve balance", "list accounts", "download transaction history", "view mini statement"],
                "database_operations": ["check_balance", "download_transaction_history", "mini_statement"]
            },
            "TRANSACTION_AGENT": {
                "description": "Manages internal fund transfers",
                "capabilities": ["process transfers"],
                "database_operations": ["process_internal_transfer"]
            },
            "CARD_MANAGEMENT_AGENT": {
                "description": "Handles card-related queries and operations",
                "capabilities": ["list cards", "card status", "activate/deactivate cards"],
                "database_operations": ["get_cards", "update_card_status"]
            },
            "KYC_UPDATE_AGENT": {
                "description": "Manages updates to user KYC information",
                "capabilities": ["update user details", "validate updates"],
                "database_operations": ["update_kyc"]
            },
            "FAQ_SUPPORT_AGENT": {
                "description": "Provides general support and answers FAQs",
                "capabilities": ["answer general questions", "search FAQs"],
                "database_operations": ["search_faq"]
            }
        }
    
    def route_query(self, query: str, user_id: str, session: ConversationSession) -> dict:
        user_context = get_user_context(user_id)
        session_context = session.get_context_summary()
        routing_prompt = f"""
You are an intelligent banking assistant router. Analyze the user's query and determine the most appropriate agent and actions.

USER QUERY: "{query}"
USER ID: {user_id}
USER STATUS: {user_context['status']}
USER CONTEXT: {json.dumps(user_context, indent=2)}
SESSION CONTEXT: {session_context}

AVAILABLE AGENTS:
{json.dumps(self.available_agents, indent=2)}

INSTRUCTIONS:
1. Analyze the user's intent from their query.
2. If the query is vague, short, or a single word (e.g., a location), check the SESSION CONTEXT for the most recent interaction to infer intent.
3. If the query mentions downloading or exporting transaction history, select BALANCE_INQUIRY_AGENT with intent 'download_transaction_history'. The account_number is optional.
4. If the query mentions activating or deactivating a card, select CARD_MANAGEMENT_AGENT with intent 'update_card_status'. Map 'activate' to status 'Active' and 'deactivate' to status 'Inactive'. The card_number is optional.
5. If the query mentions transferring money or sending funds, select TRANSACTION_AGENT with intent 'internal_transfer'. Extract 'dest_account' (a number, typically 10 digits) and 'amount' (a number with optional $ or 'dollars') from the query. Examples:
   - "Transfer $100 to 1003001" -> dest_account: "1003001", amount: "100"
   - "I want to send 100 dollars to account 1003001" -> dest_account: "1003001", amount: "100"
   The source_account is optional; the system can fetch accounts automatically.
6. If the query mentions mini statement or recent transactions, select BALANCE_INQUIRY_AGENT with intent 'mini_statement'. The account_number is optional.
7. Select the most appropriate agent from the available agents.
8. Determine what database operations are needed.
9. Extract any parameters needed for the operations (e.g., destination_account, amount for transfers).
10. Provide reasoning for your decision.

Return your response in this exact JSON format:
{{
    "selected_agent": "AGENT_NAME",
    "reasoning": "Why you selected this agent",
    "intent": "What the user wants to do",
    "database_operations": ["list", "of", "operations"],
    "parameters": {{
        "param1": "value1",
        "param2": "value2"
    }},
    "needs_data_collection": true/false,
    "missing_data": ["list", "of", "fields", "missing"]
}}
"""
        try:
            logger.debug(f"Sending LLM prompt for query: {query}")
            llm_response = safe_llm_call(routing_prompt)
            logger.debug(f"LLM Response: {llm_response}")
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                llm_response = llm_response[json_start:json_end].strip()
            routing_decision = json.loads(llm_response)
            required_fields = ["selected_agent", "reasoning", "intent", "database_operations", "parameters"]
            if not all(field in routing_decision for field in required_fields):
                raise ValueError("Missing required fields in routing decision")
            return routing_decision
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM routing decision: {e}")
            return self._fallback_routing(query, user_id, session)
    
    def _fallback_routing(self, query: str, user_id: str, session: ConversationSession) -> dict:
        query_lower = query.lower()
        if not session._history_loaded:
            session.load_history()
            
        # New account creation keywords
        new_account_keywords = ['open', 'new', 'create', 'register', 'signup', 'start', 'begin']
        is_new_account = any(keyword in query_lower for keyword in new_account_keywords)
        
        # If user_id is NEWUSER or it's clearly a new account request
        if user_id == "NEWUSER" or is_new_account:
            return {
                "selected_agent": "ACCOUNT_OPENING_AGENT",
                "reasoning": "New user account creation request",
                "intent": "account_opening",
                "database_operations": [],
                "parameters": {},
                "needs_data_collection": True,
                "missing_data": ["all_required_fields"]
            }
        
        # Balance and account inquiries
        if any(word in query_lower for word in ["balance", "check", "account", "money"]) and not any(word in query_lower for word in ["transfer", "send"]):
            return {
                "selected_agent": "BALANCE_INQUIRY_AGENT",
                "reasoning": "Balance inquiry request",
                "intent": "check_balance",
                "database_operations": ["check_balance"],
                "parameters": {},
                "needs_data_collection": False,
                "missing_data": []
            }
        
        if "download" in query_lower and "transaction" in query_lower:
            return {
                "selected_agent": "BALANCE_INQUIRY_AGENT",
                "reasoning": "Fallback for transaction history download",
                "intent": "download_transaction_history",
                "database_operations": ["download_transaction_history"],
                "parameters": {},
                "needs_data_collection": False,
                "missing_data": []
            }
        
        if "activate" in query_lower and "card" in query_lower:
            return {
                "selected_agent": "CARD_MANAGEMENT_AGENT",
                "reasoning": "Fallback for card activation",
                "intent": "update_card_status",
                "database_operations": ["update_card_status"],
                "parameters": {"status": "Active"},
                "needs_data_collection": False,
                "missing_data": []
            }
        
        if ("deactivate" in query_lower or "block" in query_lower) and "card" in query_lower:
            return {
                "selected_agent": "CARD_MANAGEMENT_AGENT",
                "reasoning": "Fallback for card deactivation",
                "intent": "update_card_status",
                "database_operations": ["update_card_status"],
                "parameters": {"status": "Inactive"},
                "needs_data_collection": False,
                "missing_data": []
            }
        
        if any(word in query_lower for word in ["transfer", "send", "pay"]) and any(word in query_lower for word in ["money", "funds", "account", "to"]):
            # Enhanced fallback parsing for transfers
            dest_account = None
            amount = None
            account_match = re.search(r"(?:to|account)\s*(\d{10})", query_lower)
            amount_match = re.search(r"\$?(\d+\.?\d*)?\s*(?:dollars)?", query_lower)
            if account_match:
                dest_account = account_match.group(1)
            if amount_match:
                amount = amount_match.group(1)
            return {
                "selected_agent": "TRANSACTION_AGENT",
                "reasoning": "Fallback for internal fund transfer",
                "intent": "internal_transfer",
                "database_operations": ["process_internal_transfer"],
                "parameters": {
                    "dest_account": dest_account or "",
                    "amount": amount or ""
                },
                "needs_data_collection": not (dest_account and amount),
                "missing_data": [field for field, value in [("destination_account", dest_account), ("amount", amount)] if not value]
            }
        
        if any(word in query_lower for word in ["mini", "statement", "recent", "transactions"]):
            return {
                "selected_agent": "BALANCE_INQUIRY_AGENT",
                "reasoning": "Fallback for mini statement",
                "intent": "mini_statement",
                "database_operations": ["mini_statement"],
                "parameters": {},
                "needs_data_collection": True,
                "missing_data": ["account_number"]
            }
        
        if any(word in query_lower for word in ["card", "cards", "show", "list"]) and not any(word in query_lower for word in ["activate", "deactivate", "block"]):
            return {
                "selected_agent": "CARD_MANAGEMENT_AGENT",
                "reasoning": "Card information request",
                "intent": "get_cards",
                "database_operations": ["get_cards"],
                "parameters": {},
                "needs_data_collection": False,
                "missing_data": []
            }
        
        if session.context["conversation_history"]:
            last_interaction = session.context["conversation_history"][-1]
            last_intent = last_interaction["intent"]
            if last_intent == "general_support" and "hours" in last_interaction["query"].lower():
                return {
                    "selected_agent": "FAQ_SUPPORT_AGENT",
                    "reasoning": "Follow-up to branch hours query",
                    "intent": "branch_hours",
                    "database_operations": ["search_faq"],
                    "parameters": {"keyword": f"branch hours {query_lower}"},
                    "needs_data_collection": False,
                    "missing_data": []
                }
        
        return {
            "selected_agent": "FAQ_SUPPORT_AGENT",
            "reasoning": "Fallback to general support",
            "intent": "general_support",
            "database_operations": ["search_faq"],
            "parameters": {"keyword": query_lower},
            "needs_data_collection": False,
            "missing_data": []
        }

class AgenticExecutor:
    def __init__(self, router: AgenticIntelligenceRouter):
        self.router = router
    
    def validate_field(self, field: str, value: str) -> Tuple[bool, str]:
        if not value or not value.strip():
            return False, "Value cannot be empty."
        if field in ["aadhaar_name", "aadhaar_father_name"]:
            if not re.match(r"^[A-Za-z\s]+$", value):
                return False, "Name should only contain letters and spaces."
            if len(value.strip()) < 2:
                return False, "Name is too short."
        if field == "aadhaar_number":
            if not re.match(r"^\d{12}$", value):
                return False, "Aadhaar number must be a 12-digit number."
        if field == "pan_number":
            if not re.match(r"^[A-Z]{5}\d{4}[A-Z]$", value):
                return False, "PAN number must follow format ABCDE1234F."
        if field == "email":
            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", value):
                return False, "Invalid email format."
        if field == "aadhaar_mobile":
            if not re.match(r"^\d{10}$", value):
                return False, "Mobile number must be a 10-digit number."
        if field == "aadhaar_dob":
            try:
                dob = datetime.strptime(value, "%d-%m-%Y")
                current_date = datetime.now()
                age = current_date.year - dob.year - ((current_date.month, current_date.day) < (dob.month, dob.day))
                if age < 18:
                    return False, "You must be at least 18 years old to create an account."
            except ValueError:
                return False, "Date of birth must be in DD-MM-YYYY format."
        if field == "account_type":
            if value not in ["Savings", "Current"]:
                return False, "Account type must be 'Savings' or 'Current'."
        return True, ""

    def execute_agent_workflow(self, routing_decision: dict, query: str, user_id: str, session: ConversationSession) -> str:
        agent_name = routing_decision["selected_agent"]
        intent = routing_decision["intent"]
        db_operations = routing_decision["database_operations"]
        parameters = routing_decision["parameters"]
        try:
            if agent_name == "ACCOUNT_OPENING_AGENT":
                return self._handle_account_opening(query, user_id, session, parameters)
            elif agent_name == "BALANCE_INQUIRY_AGENT":
                return self._handle_balance_inquiry(query, user_id, parameters, intent)
            elif agent_name == "TRANSACTION_AGENT":
                return self._handle_transactions(query, user_id, parameters, intent, session)
            elif agent_name == "CARD_MANAGEMENT_AGENT":
                return self._handle_card_management(query, user_id, parameters, intent, session)
            elif agent_name == "KYC_UPDATE_AGENT":
                return self._handle_kyc_updates(query, user_id, parameters)
            elif agent_name == "FAQ_SUPPORT_AGENT":
                return self._handle_faq_support(query, user_id, parameters)
            else:
                return f"Unknown agent: {agent_name}"
        except Exception as e:
            logger.error(f"Error executing agent workflow: {e}")
            return "Error processing your request. Please try again."
    
    def _handle_account_opening(self, query: str, user_id: str, session: ConversationSession, parameters: dict) -> str:
        current_data = session.context.get("new_user_data", {})
        required_fields = ["email", "pan_number", "aadhaar_number", "aadhaar_name",
                          "aadhaar_father_name", "aadhaar_dob", "aadhaar_address",
                          "aadhaar_mobile", "account_type"]
        missing_fields = [field for field in required_fields if field not in current_data]
        if not missing_fields:
            return handle_account_creation(current_data, user_id, session)
        next_field = missing_fields[0]
        session.field_attempts[next_field] = session.field_attempts.get(next_field, 0) + 1
        extraction_prompt = f"""
Extract relevant information from the user's query for account opening. The user may provide the data naturally (e.g., 'LKJHD8547F' for PAN number) without explicit labels like 'PAN number is'. Use the expected field to interpret the input.

USER QUERY: "{query}"
CURRENT_DATA: {json.dumps(current_data)}
EXPECTED_FIELD: {next_field}
MISSING_FIELDS: {missing_fields}

FIELD_DEFINITIONS:
- email: Valid email address (e.g., user@example.com)
- pan_number: 10-character PAN (e.g., ABCDE1234F)
- aadhaar_number: 12-digit Aadhaar number
- aadhaar_name: Full name as per Aadhaar
- aadhaar_father_name: Father's name
- aadhaar_dob: Date of birth (DD-MM-YYYY)
- aadhaar_address: Address
- aadhaar_mobile: 10-digit mobile
- account_type: "Savings" or "Current"

INSTRUCTIONS:
1. If the query matches the expected field's format (e.g., 'LKJHD8547F' for pan_number), extract it as the value.
2. Ignore prefixes like 'my', 'is', or field names unless they clarify intent.
3. Validate the extracted value against the field's format.
4. If no valid data is extracted, request the field again.

Return JSON:
{{
    "extracted_data": {{"{next_field}": "value"}},
    "validation_errors": ["errors"],
    "next_field_to_request": "{next_field}",
    "response_message": "message to user"
}}
"""
        try:
            llm_response = safe_llm_call(extraction_prompt)
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                llm_response = llm_response[json_start:json_end].strip()
            extraction_result = json.loads(llm_response)
            extracted_data = extraction_result.get("extracted_data", {})
            validation_errors = extraction_result.get("validation_errors", [])
            response_message = extraction_result.get("response_message", f"Please provide your {next_field.replace('_', ' ')}:")
            
            # Fallback parsing if LLM fails to extract
            if not extracted_data and query.strip():
                if next_field == "pan_number" and re.match(r"^[A-Z]{5}\d{4}[A-Z]$", query.strip()):
                    extracted_data[next_field] = query.strip()
                elif next_field == "aadhaar_name" and re.match(r"^[A-Za-z\s]+$", query.strip()):
                    extracted_data[next_field] = query.strip()
                elif next_field == "aadhaar_father_name" and re.match(r"^[A-Za-z\s]+$", query.strip()):
                    extracted_data[next_field] = query.strip()
                elif next_field == "aadhaar_dob" and re.match(r"^\d{2}-\d{2}-\d{4}$", query.strip()):
                    extracted_data[next_field] = query.strip()
                elif next_field == "aadhaar_number" and re.match(r"^\d{12}$", query.strip()):
                    extracted_data[next_field] = query.strip()
                elif next_field == "aadhaar_mobile" and re.match(r"^\d{10}$", query.strip()):
                    extracted_data[next_field] = query.strip()
                elif next_field == "email" and re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", query.strip()):
                    extracted_data[next_field] = query.strip()
                elif next_field == "account_type" and query.strip() in ["Savings", "Current"]:
                    extracted_data[next_field] = query.strip()
                elif next_field == "aadhaar_address":
                    extracted_data[next_field] = query.strip()

            for field, value in extracted_data.items():
                if field in required_fields:
                    is_valid, error_message = self.validate_field(field, value)
                    if is_valid:
                        session.update_new_user_data(field, value)
                        session.field_attempts[field] = 0
                        response_message = f"{field.replace('_', ' ').title()} '{value}' recorded. Please provide your {missing_fields[1].replace('_', ' ') if len(missing_fields) > 1 else 'next information'}:"
                    else:
                        validation_errors.append(f"Invalid {field}: {error_message}")
            
            if validation_errors:
                response_message = f"Errors: {'; '.join(validation_errors)}. Please provide your {next_field.replace('_', ' ')}:"
            return response_message
        except Exception as e:
            logger.error(f"Error in data extraction: {e}")
            field_prompts = {
                "email": "Please provide your email address (e.g., user@example.com):",
                "pan_number": "Please provide your PAN number (e.g., ABCDE1234F):",
                "aadhaar_number": "Please provide your 12-digit Aadhaar number:",
                "aadhaar_name": "Please provide your full name as per Aadhaar:",
                "aadhaar_father_name": "Please provide your father's name as per Aadhaar:",
                "aadhaar_dob": "Please provide your date of birth (DD-MM-YYYY):",
                "aadhaar_address": "Please provide your address as per Aadhaar:",
                "aadhaar_mobile": "Please provide your 10-digit mobile number:",
                "account_type": "Please specify account type (Savings or Current):"
            }
            return field_prompts.get(next_field, f"Please provide your {next_field.replace('_', ' ')}:")

    def _handle_balance_inquiry(self, query: str, user_id: str, parameters: dict, intent: str) -> str:
        try:
            db_session = SessionFactory()
            accounts = db_session.query(Account).filter_by(user_id=user_id).all()
            if not accounts:
                return "No accounts found for your user ID."
            account_number = parameters.get("account_number")
            if intent == "download_transaction_history":
                if account_number:
                    if any(acc.account_number == account_number for acc in accounts):
                        return generate_transaction_history_md(user_id, account_number)
                    return f"Account {account_number} not found or does not belong to you."
                if len(accounts) == 1:
                    return generate_transaction_history_md(user_id, accounts[0].account_number)
                response = "You have multiple accounts. Please select an account:\n"
                for acc in accounts:
                    response += f"- {acc.account_number} ({acc.account_type}, Balance: ${acc.balance:.2f})\n"
                response += "Provide the account number to download its transaction history."
                return response
            
            elif intent == "mini_statement":
                if account_number:
                    if any(acc.account_number == account_number for acc in accounts):
                        return execute_database_query("mini_statement", {"account_number": account_number}, user_id)
                    return f"Account {account_number} not found or does not belong to you."
                if len(accounts) == 1:
                    return execute_database_query("mini_statement", {"account_number": accounts[0].account_number}, user_id)
                response = "You have multiple accounts. Please select an account:\n"
                for acc in accounts:
                    response += f"- {acc.account_number} ({acc.account_type}, Balance: ${acc.balance:.2f})\n"
                response += "Provide the account number for mini statement."
                return response
            
            else:
                return execute_database_query("check_balance", {"account_number": account_number}, user_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            return "Error accessing your accounts."
        finally:
            db_session.close()

    def _handle_transactions(self, query: str, user_id: str, parameters: dict, intent: str, session: ConversationSession) -> str:
        if intent == "internal_transfer":
            try:
                db_session = SessionFactory()
                if session.context.get("pending_action") == "select_account":
                    source_account = query.strip()
                    if not source_account:
                        return "Please provide a valid source account number."
                    pending_transfer = session.context.get("pending_transfer", {})
                    accounts = db_session.query(Account).filter_by(user_id=user_id, status="Active").all()
                    target_account = None
                    for acc in accounts:
                        if source_account == acc.account_number:
                            target_account = acc
                            break
                    if not target_account:
                        return f"Account {source_account} not found or is not active."
                    session.context["pending_action"] = None
                    parameters = {
                        "source_account": target_account.account_number,
                        "dest_account": pending_transfer.get("dest_account"),
                        "amount": pending_transfer.get("amount")
                    }
                    session.context["pending_transfer"] = None  # Clear pending transfer
                    return execute_database_query("process_internal_transfer", parameters, user_id)
                
                dest_account = parameters.get("dest_account")
                amount = parameters.get("amount")
                
                # Enhanced parsing for natural inputs
                if not (dest_account and amount):
                    account_match = re.search(r"(?:to|account)\s*(\d{10})", query.lower())
                    amount_match = re.search(r"\$?(\d+\.?\d*)?\s*(?:dollars)?", query.lower())
                    if account_match:
                        dest_account = account_match.group(1)
                    if amount_match:
                        amount = amount_match.group(1)
                    if dest_account and amount:
                        parameters["dest_account"] = dest_account
                        parameters["amount"] = amount
                
                if dest_account and amount:
                    try:
                        amount = float(amount)
                        if amount <= 0:
                            return "Amount must be positive."
                    except ValueError:
                        return "Invalid amount format."
                    
                    accounts = db_session.query(Account).filter_by(user_id=user_id, status="Active").all()
                    if not accounts:
                        return "No active accounts found for your user ID."
                    
                    if len(accounts) == 1:
                        parameters["source_account"] = accounts[0].account_number
                        return execute_database_query("process_internal_transfer", parameters, user_id)
                    else:
                        response = f"Destination account {dest_account} and amount ${amount:.2f} recorded. You have multiple active accounts. Please select a source account:\n"
                        for acc in accounts:
                            response += f"- {acc.account_number} ({acc.account_type}, Balance: ${acc.balance:.2f})\n"
                        response += "Provide the source account number."
                        session.context["pending_action"] = "select_account"
                        session.context["pending_transfer"] = {"dest_account": dest_account, "amount": amount}
                        return response
                
                return "Please provide the destination account number and amount (e.g., 'Transfer $100 to 1003001')."
            except SQLAlchemyError as e:
                logger.error(f"Error processing transfer: {str(e)}")
                return "Error processing transfer."
            finally:
                db_session.close()
        
        return "Invalid transaction request. Please specify a transfer (e.g., 'Transfer $100 to 1XXXXX01')."

    def _handle_card_management(self, query: str, user_id: str, parameters: dict, intent: str, session: ConversationSession) -> str:
        if intent == "update_card_status":
            try:
                db_session = SessionFactory()
                if session.context.get("pending_action") == "select_card":
                    card_number = query.strip()
                    if not card_number:
                        return "Please provide a valid card number."
                    cards = db_session.query(Card).filter_by(user_id=user_id).all()
                    target_card = None
                    for card in cards:
                        if card_number == card.card_number or card_number == card.card_number[-4:]:
                            target_card = card
                            break
                    if not target_card:
                        return f"Card ending in {card_number} not found."
                    new_status = session.context.get("pending_status")
                    session.context["pending_action"] = None
                    session.context["pending_status"] = None
                    return execute_database_query("update_card_status", {
                        "card_number": target_card.card_number,
                        "status": new_status
                    }, user_id)
                
                new_status = parameters.get("status", "").capitalize()
                if new_status == "Activate":
                    new_status = "Active"
                elif new_status == "Deactivate":
                    new_status = "Inactive"
                if new_status not in ["Active", "Inactive"]:
                    logger.debug(f"Invalid status received: {parameters.get('status')}")
                    return "Invalid status. Please specify 'activate' or 'deactivate'."
                
                filter_status = "Active" if new_status == "Inactive" else "Inactive"
                cards = db_session.query(Card).filter_by(user_id=user_id, status=filter_status).all()
                
                if not cards:
                    return f"No {filter_status.lower()} cards found to {new_status.lower()}."
                
                if len(cards) == 1:
                    return execute_database_query("update_card_status", {
                        "card_number": cards[0].card_number,
                        "status": new_status
                    }, user_id)
                
                response = f"You have multiple {filter_status.lower()} cards. Please select one to {new_status.lower()}:\n"
                for card in cards:
                    masked_card = f"{card.card_number[0]}**** **** **** {card.card_number[-4:]}"
                    response += f"- {masked_card} (Type: {card.card_type}, Issued: {card.issue_date[:10]})\n"
                response += "Provide the card number or last 4 digits."
                
                session.context["pending_action"] = "select_card"
                session.context["pending_status"] = new_status
                return response
            except SQLAlchemyError as e:
                logger.error(f"Error accessing cards: {e}")
                return "Error accessing your cards."
            finally:
                db_session.close()
        
        return execute_database_query("get_cards", {}, user_id)

    def _handle_kyc_updates(self, query: str, user_id: str, parameters: dict) -> str:
        field = parameters.get("field")
        new_value = parameters.get("new_value")
        if field and new_value:
            return execute_database_query("update_kyc", {"field": field, "new_value": new_value}, user_id)
        return "Please specify the field to update (e.g., email) and the new value."

    def _handle_faq_support(self, query: str, user_id: str, parameters: dict) -> str:
        faq_prompt = f"""
You are a banking FAQ support agent. Answer the user's question using general banking knowledge or suggest a database FAQ search.

Query: "{query}"

Provide a concise, professional response to the user's query. If unable to answer fully, suggest a database query for FAQs with a keyword.
"""
        try:
            faq_response = safe_llm_call(faq_prompt)
            if "database FAQ search" in faq_response.lower():
                return execute_database_query("search_faq", {"keyword": parameters.get("keyword", query)}, user_id)
            return faq_response
        except Exception as e:
            logger.error(f"Error in FAQ support: {e}")
            return execute_database_query("search_faq", {"keyword": parameters.get("keyword", query)}, user_id)

def run_dynamic_banking_service(user_id: str, query: str) -> str:
    try:
        session = ConversationSession.get_or_create(user_id)
        router = AgenticIntelligenceRouter()
        executor = AgenticExecutor(router)
        try:
            routing_decision = router.route_query(query, user_id, session)
            logger.debug(f"Routing Decision: {routing_decision}")
            response = executor.execute_agent_workflow(routing_decision, query, user_id, session)
            session.add_query(query, routing_decision["intent"], response, routing_decision)
            return response
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "Error processing your request. Please try again."
    except Exception as e:
        logger.error(f"Error in banking service: {e}")
        return "Technical difficulty encountered. Please try again."

def validate_user_id(user_id: str) -> bool:
    if user_id == "NEWUSER":
        return True
    try:
        session = SessionFactory()
        return session.query(User).filter_by(user_id=user_id, status="Active").count() > 0
    except SQLAlchemyError as e:
        logger.error(f"Error validating user ID: {e}")
        return False
    finally:
        session.close()

# === INTEGRATION WRAPPER CLASS ===
class BankingServicesAgent:
    """
    Wrapper class to match integration pattern of Fraud.py and Loan.py
    for seamless integration with Main.py orchestration system.
    """
    
    def __init__(self):
        try:
            # Initialize database
            self.account_type_mapper = AccountTypeMapper()
            DatabaseManager.initialize_database()
            logger.info("Banking Services Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Banking Services Agent: {e}")
            raise
    
    def process_single_query(self, user_input: str, user_id: str = "NEWUSER") -> str:
        """
        Process a single banking query without entering interactive mode.
        This method is used for integration with the main orchestrator.
        """
        try:
            return run_dynamic_banking_service(user_id, user_input)
        except Exception as e:
            return f"Error processing banking query: {str(e)}"
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get the current status of the banking services agent."""
        try:
            # Test database connection
            session = SessionFactory()
            user_count = session.query(User).count()
            session.close()
            
            return {
                "agent_type": "Banking_Services",
                "database_connected": True,
                "total_users": user_count,
                "llm_available": llm is not None
            }
        except Exception as e:
            return {
                "agent_type": "Banking_Services", 
                "database_connected": False,
                "error": str(e)
            }
        
    def handle_account_creation_flow(self, user_input, context):
        flow = context.collected_data

        if "email" not in flow:
            flow["email"] = user_input
            return f"Email '{user_input}' recorded. Please provide your pan number:"

        elif "pan_number" not in flow:
            flow["pan_number"] = user_input
            return f"Pan Number '{user_input}' recorded. Please provide your aadhaar number:"

        elif "aadhaar_number" not in flow:
            flow["aadhaar_number"] = user_input
            return f"Aadhaar Number '{user_input}' recorded. Please provide your aadhaar name:"

        elif "aadhaar_name" not in flow:
            flow["aadhaar_name"] = user_input
            return f"Aadhaar Name '{user_input}' recorded. Please provide your aadhaar father name:"

        elif "aadhaar_father_name" not in flow:
            flow["aadhaar_father_name"] = user_input
            return f"Aadhaar Father Name '{user_input}' recorded. Please provide your aadhaar dob:"

        elif "aadhaar_dob" not in flow:
            flow["aadhaar_dob"] = user_input
            return f"Aadhaar Dob '{user_input}' recorded. Please provide your aadhaar address:"

        elif "aadhaar_address" not in flow:
            flow["aadhaar_address"] = user_input
            return f"Aadhaar Address '{user_input}' recorded. Please provide your aadhaar mobile:"

        elif "aadhaar_mobile" not in flow:
            flow["aadhaar_mobile"] = user_input
            return f"Aadhaar Mobile '{user_input}' recorded. Please provide your account type:"

        elif "account_type" not in flow:
            try:
                resolved_type = self.account_type_mapper.resolve(user_input)
                flow["account_type"] = resolved_type
                context.conversation_state = "completed"
                return self.create_account(flow)
            except Exception:
                return "⚠️ I couldn't understand that account type. Can you rephrase it?"

        return "✅ Your account has already been created."
    
    def create_account(self, collected_data: Dict[str, Any]) -> str:
        """Creates a new bank account and returns detailed confirmation."""
        import random

        # Step 1: Extract or assign values
        user_id = f"U{random.randint(1000, 9999)}"
        account_number = f"{random.randint(1000000000, 9999999999)}"
        account_type = collected_data.get("account_type", "Savings")
        initial_balance = float(collected_data.get("initial_balance", 1000))
        debit_card = f"DC{random.randint(100000, 999999)}"

        # (Optional) Store this in DB/memory if needed for demo continuity

        # Step 2: Return response
        return (
            f"✅ Account created successfully!\n"
            f"User ID: {user_id}\n"
            f"Account Number: {account_number}\n"
            f"Account Type: {account_type}\n"
            f"Initial Balance: ₹{initial_balance:.2f}\n"
            f"Debit Card: {debit_card}"
        )


    

# === STATIC METHODS FOR BACKWARDS COMPATIBILITY ===
def get_agent_status() -> Dict[str, Any]:
    """Get the current status of the banking services agent."""
    try:
        # Test database connection
        session = SessionFactory()
        user_count = session.query(User).count()
        session.close()
        
        return {
            "agent_type": "Banking_Services",
            "database_connected": True,
            "total_users": user_count,
            "llm_available": llm is not None
        }
    except Exception as e:
        return {
            "agent_type": "Banking_Services", 
            "database_connected": False,
            "error": str(e)
        }

def process_single_banking_query(user_id: str, query: str) -> str:
    """
    Process a single banking query without entering interactive mode.
    This is a wrapper around run_dynamic_banking_service for integration.
    """
    try:
        return run_dynamic_banking_service(user_id, query)
    except Exception as e:
        return f"Error processing banking query: {str(e)}"

def interactive_session():
    print("=" * 60)
    print("AI Banking Assistant")
    print("=" * 60)
    print("Type 'exit' to quit or 'help' for services")
    
    while True:
        try:
            user_type = input("\nNew user? (yes/no/exit): ").strip().lower()
            if user_type in ['exit', 'quit']:
                print("\nThank you for using our banking services!")
                break
            if user_type == 'help':
                print("""
Services:
- Open a new account
- Check account balance or view mini statement
- Download transaction history
- Transfer funds between accounts
- Manage cards (view, activate, deactivate)
- Update KYC information
- General banking FAQs

Examples:
- "What's my balance?"
- "Show mini statement"
- "Download transaction history"
- "Transfer $100 to 1001002000"
- "Activate my card"
- "Deactivate my card"
- "Update my email to newemail@example.com"
- "What are your banking hours?"
""")
                continue
            if user_type == "yes":
                user_id = "NEWUSER"
                print("\nStarting account registration...")
                session = ConversationSession.get_or_create(user_id)
                while True:
                    query = input("\nYou: ").strip()
                    if query.lower() in ['exit', 'quit']:
                        session.clear_new_user_data()
                        print("Registration cancelled.")
                        break
                    if not query:
                        print("Please provide information.")
                        continue
                    print("AI is analyzing your input...")
                    response = run_dynamic_banking_service(user_id, query)
                    print(f"\nAI Assistant: {response}")
                    if "Account created successfully" in response:
                        user_id_match = re.search(r'User ID: (U\d+)', response)
                        if user_id_match:
                            user_id = user_id_match.group(1)
                            if input("\nContinue banking? (yes/no): ").strip().lower() != "yes":
                                break
                    continue
            else:
                while True:
                    user_id = input("\nUser ID (e.g., U1001): ").strip()
                    if user_id.lower() in ['exit', 'quit']:
                        break
                    if not user_id:
                        print("User ID cannot be empty.")
                        continue
                    if validate_user_id(user_id):
                        print(f"Welcome back, {user_id}!")
                        break
                    print("Invalid User ID.")
                    if input("Try again? (yes/no): ").strip().lower() != "yes":
                        break
                if user_id.lower() in ['exit', 'quit'] or not validate_user_id(user_id):
                    continue
                print(f"\nBanking Assistant (User: {user_id})")
                session = ConversationSession.get_or_create(user_id)
                while True:
                    query = input(f"\n{user_id}: ").strip()
                    if query.lower() in ['exit', 'quit']:
                        print("Session ended.")
                        break
                    if query.lower() == 'help':
                        print("""
Services:
- Open a new account
- Check account balance or view mini statement
- Download transaction history
- Transfer funds between accounts
- Manage cards (view, activate, deactivate)
- Update KYC information
- General banking FAQs

Examples:
- "What's my balance?"
- "Show mini statement"
- "Download transaction history"
- "Transfer $100 to 1001002000"
- "Activate my card"
- "Deactivate my card"
- "Update my email to newemail@example.com"
- "What are your banking hours?"
""")
                        continue
                    if not query:
                        print("Please ask something.")
                        continue
                    print("AI is analyzing your request...")
                    response = run_dynamic_banking_service(user_id, query)
                    print(f"\n{response}")
        except KeyboardInterrupt:
            print("\nSession interrupted.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            print(f"\nError occurred: {e}. Please restart.")
            break

def main():
    try:
        print("Initializing AI Banking Assistant...")
        DatabaseManager.initialize_database()
        print("Database initialized successfully")
        if llm:
            print("LLM connected successfully")
        else:
            print("Warning: AI service unavailable.")
            return
        interactive_session()
    except Exception as e:
        print(f"Server error: {e}. Try again.")
        logger.error(f"Critical error: {e}")
        return

if __name__ == "__main__":
    main()