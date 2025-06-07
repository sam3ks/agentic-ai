import os
import pandas as pd
import numpy as np
import json
import re
import warnings
from typing import Any, Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# LangChain imports
from langchain.llms.base import LLM
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.callbacks.base import BaseCallbackHandler

# Groq imports
from groq import Groq

warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# Custom callback for debugging AgentExecutor steps
class DebugCallback(BaseCallbackHandler):
    def on_agent_action(self, action, **kwargs):
        print(f"[DEBUG] Agent Action: {action.tool} with input: {action.tool_input}")
    def on_agent_observation(self, observation, **kwargs):
        print(f"[DEBUG] Agent Observation: {observation}")
    def on_agent_finish(self, finish, **kwargs):
        print(f"[DEBUG] Agent Finish: {finish}")

class Loan_processing_AI_agent2:
    """Configuration and implementation for the loan processing system."""
    
    class Config:
        """Configuration management for the loan processing system."""
        
        def __init__(self):
            self.groq_api_key = self._get_groq_api_key()
            self.dataset_path = 'Loan_Dataset_V1.csv'
            self.max_loan_amount = 2000000
            self.min_credit_score = 300
            self.max_credit_score = 850
    
        def _get_groq_api_key(self) -> str:
            """Get Groq API key from environment variables."""
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                print("⚠️ GROQ_API_KEY not found. System may use fallback mode.")
                return ""
            return api_key
    
    class GroqLLM(LLM):
        """Custom Groq LLM wrapper for LangChain with rate limiting and fallback."""
        
        model_name: str = "llama-3.3-70b-versatile"
        temperature: float = 0.1
        max_tokens: int = 1024
        groq_client: Any = None
        config: Any = None
    
        def __init__(self, config=None, **kwargs):
            super().__init__(**kwargs)
            self.config = config
            if config and config.groq_api_key:
                try:
                    self.groq_client = Groq(api_key=config.groq_api_key)
                except Exception as e:
                    print(f"⚠️ Failed to initialize Groq client: {e}")
                    self.groq_client = None
            else:
                self.groq_client = None
            
            # Initialize tracking variables as regular instance attributes
            object.__setattr__(self, '_call_count', 0)
            object.__setattr__(self, '_last_call_time', 0.0)
    
        @property
        def _llm_type(self) -> str:
            return "groq"
    
        def _call(self, prompt: str, stop: Optional[List[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs) -> str:
            """Call the Groq API with rate limiting and error handling."""
            import time
            
            if not self.groq_client:
                return f"Groq client not available. Using fallback analysis for prompt: {prompt[:100]}..."
            
            # Simple rate limiting
            current_time = time.time()
            last_call_time = getattr(self, '_last_call_time', 0.0)
            if current_time - last_call_time < 1.0:  # Wait at least 1 second between calls
                time.sleep(1.0)
            
            object.__setattr__(self, '_last_call_time', time.time())
            call_count = getattr(self, '_call_count', 0) + 1
            object.__setattr__(self, '_call_count', call_count)
            
            try:
                response = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    **kwargs
                )
                
                result = response.choices[0].message.content
                
                if stop:
                    for stop_word in stop:
                        if stop_word in result:
                            result = result[:result.index(stop_word)]
                            break
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    return f"Rate limit reached. Using fallback analysis. Call #{call_count}"
                elif "API" in error_msg:
                    return f"API Error: {error_msg}. Using fallback analysis."
                else:
                    return f"Analysis Error: {error_msg}"
    
    class LoanDataManager:
        """Manages loan dataset operations."""
        
        def __init__(self, dataset_path: str):
            if not os.path.exists(dataset_path):
                print(f"⚠️ Dataset {dataset_path} not found. Creating sample dataset.")
            self.df = self._load_or_create_dataset(dataset_path)
    
        def _load_or_create_dataset(self, path: str) -> pd.DataFrame:
            """Load existing dataset or create sample data."""
            if os.path.exists(path):
                try:
                    df = pd.read_csv(path)
                    print(f"✓ Loading loan dataset with {df.shape[0]} records")
                except Exception as e:
                    print(f"⚠️ Error loading dataset: {e}. Creating sample data.")
                    df = self._create_sample_dataset()
            else:
                print("✓ Creating sample loan dataset")
                df = self._create_sample_dataset()
            
            return self._process_dataset(df)
    
        def _create_sample_dataset(self) -> pd.DataFrame:
            """Create sample dataset for testing."""
            np.random.seed(42)
            
            data = {
                'pan_number': ['ABCDE1234F', 'FGHIJ5678K', 'KLMNO9012P', 'PQRST3456U', 'VWXYZ7890A'],
                'aadhaar_number': ['123456789012', '234567890123', '345678901234', '456789012345', '567890123456'],
                'monthly_salary': [50000, 75000, 100000, 40000, 120000],
                'existing_emi': [5000, 10000, 15000, 8000, 20000],
                'credit_score': [720, 680, 760, 600, 800],
                'emi_to_income_ratio': [20, 30, 15, 35, 25],
                'delayed_payments': [1, 3, 0, 4, 0],
                'avg_monthly_balance': [25000, 35000, 50000, 15000, 60000],
                'avg_daily_transactions': [5, 8, 12, 3, 15],
                'city': ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata']
            }
            
            return pd.DataFrame(data)
    
        def _process_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
            """Process and enhance dataset."""
            # Standardize column names
            df = df.rename(columns={'PAN': 'pan_number', 'Aadhaar': 'aadhaar_number'})
            
            # Fill missing values
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)
            
            # Add city information if not exists
            if 'city' not in df.columns:
                df['city'] = np.random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata',
                                             'Hyderabad', 'Pune', 'Ahmedabad', 'Surat', 'Jaipur'],
                                            size=len(df))
            
            return df
    
        def get_user_data(self, identifier: str) -> Dict:
            """Query user data by PAN or Aadhaar."""
            try:
                mask = (self.df['pan_number'] == identifier) | (self.df['aadhaar_number'] == identifier)
                result = self.df[mask]
                
                if result.empty:
                    print(f"⚠️ User not found: {identifier}. Please provide additional details.")
                    # Prompt for basic financial details to create a temporary profile
                    monthly_salary = input("Please enter your monthly salary (₹): ").strip()
                    credit_score = input("Please enter your credit score (300-850): ").strip()
                    existing_emi = input("Please enter your existing EMI (₹, enter 0 if none): ").strip()
                    
                    try:
                        monthly_salary = float(monthly_salary) if monthly_salary else 0
                        credit_score = int(credit_score) if credit_score else 0
                        existing_emi = float(existing_emi) if existing_emi else 0
                    except ValueError:
                        return {"error": "Invalid input for financial details. Please provide numeric values."}
                    
                    # Create a temporary user profile
                    user_data = {
                        "pan_number": identifier if re.match(r'^[A-Z]{5}\d{4}[A-Z]$', identifier) else None,
                        "aadhaar_number": identifier if re.match(r'^\d{12}$', identifier) else None,
                        "monthly_salary": monthly_salary,
                        "credit_score": credit_score,
                        "existing_emi": existing_emi,
                        "delayed_payments": 0,  # Default for new users
                        "avg_monthly_balance": monthly_salary * 0.5,  # Estimate
                        "avg_daily_transactions": 5  # Default
                    }
                    return user_data
                
                user_data = result.iloc[0].to_dict()
                
                # Clean data types
                for key, value in user_data.items():
                    if pd.isna(value):
                        user_data[key] = None
                    elif hasattr(value, 'item'):
                        user_data[key] = value.item()
                
                return user_data
                
            except Exception as e:
                return {"error": f"Query failed: {str(e)}"}
    
    class DataQueryAgent:
        """Specialized agent for data querying with LLM-driven logic."""
        
        def __init__(self, data_manager: 'Loan_processing_AI_agent2.LoanDataManager', config=None):
            self.data_manager = data_manager
            self.llm = Loan_processing_AI_agent2.GroqLLM(config=config)
    
        def query_user_data(self, query: str) -> str:
            """Query user data with LLM-driven validation and processing."""
            try:
                # Use LLM to extract and validate identifier
                validation_prompt = f"""Extract PAN or Aadhaar from: "{query}"
    
    PAN format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F)
    Aadhaar format: 12 digits (e.g., 123456789012)
    
    Return only the identifier, nothing else."""
                
                try:
                    identifier = self.llm._call(validation_prompt).strip()
                except:
                    # Fallback parsing
                    identifier = query.strip()
                    if identifier.startswith('identifier:'):
                        identifier = identifier.split(':', 1)[1].strip()
                
                # Query the data
                user_data = self.data_manager.get_user_data(identifier)
                
                if "error" in user_data:
                    return json.dumps(user_data)
                
                # Remove city from data - it should be asked from user
                if 'city' in user_data:
                    del user_data['city']
                
                # Basic financial analysis
                try:
                    monthly_salary = user_data.get('monthly_salary', 0)
                    credit_score = user_data.get('credit_score', 0)
                    existing_emi = user_data.get('existing_emi', 0)
                    
                    if credit_score >= 750:
                        credit_rating = "Excellent"
                    elif credit_score >= 700:
                        credit_rating = "Good"
                    elif credit_score >= 650:
                        credit_rating = "Fair"
                    else:
                        credit_rating = "Poor"
                    
                    affordability = "High" if monthly_salary > 75000 else "Medium" if monthly_salary > 40000 else "Limited"
                    
                    analysis = {
                        "user_data": user_data,
                        "financial_assessment": {
                            "credit_rating": credit_rating,
                            "income_level": affordability,
                            "monthly_disposable_income": monthly_salary - existing_emi,
                            "existing_debt_burden": f"₹{existing_emi:,.0f} per month"
                        },
                        "status": "data_retrieved_successfully"
                    }
                    
                    return json.dumps(analysis, indent=2)
                    
                except:
                    return json.dumps({"user_data": user_data, "status": "data_retrieved"}, indent=2)
                    
            except Exception as e:
                return json.dumps({"error": f"Data query error: {str(e)}"})
    
    class GeoPolicyAgent:
        """Specialized agent for geographic policy validation with LLM-driven logic."""
        
        def __init__(self, config=None):
            self.llm = Loan_processing_AI_agent2.GroqLLM(config=config)
    
        def validate_geo_policy(self, query: str) -> str:
            """Validate geographic policies using LLM reasoning."""
            try:
                # Use LLM to parse and validate the policy request
                parsing_prompt = f"""
You are a loan policy expert. Parse this geographic policy validation request:

Query: "{query}"

Extract and validate:
1. City name
2. Loan purpose/type
3. Loan amount

Indian cities we serve: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Surat, Jaipur

Loan purposes: Home Renovation, Car, Education, Business, Medical, Wedding, Personal, Travel, Debt Consolidation

Respond in JSON format:
{{
    "city": "extracted_city",
    "purpose": "normalized_purpose",
    "amount": numeric_amount,
    "valid_request": true,
    "errors": []
}}
"""
                try:
                    parsing_result = self.llm._call(parsing_prompt)
                except Exception as e:
                    return json.dumps({"error": f"Policy parsing service unavailable: {str(e)}"})
                
                try:
                    parsed_data = json.loads(parsing_result)
                except ValueError:
                    return json.dumps({"error": "Failed to parse policy response"})
                
                if not parsed_data.get("valid_request", False):
                    return json.dumps({"error": f"Invalid request: {', '.join(parsed_data.get('errors', []))}"})
                
                city = parsed_data["city"]
                purpose = parsed_data["purpose"]
                amount = parsed_data["amount"]
                
                # Use LLM to make policy decisions
                policy_prompt = f"""
You are a senior loan policy officer. Make a geographic policy decision for this loan:

City: {city}
Loan Purpose: {purpose}
Requested Amount: ₹{amount:,.0f}

Indian Banking Regulations and City-wise Policies:
- Mumbai: High-value city, max loan ₹20,00,000, all purposes allowed
- Delhi: Capital city, max loan ₹15,00,000, government sector friendly
- Bangalore: Tech hub, max loan ₹20,00,000, business loans preferred
- Chennai: Industrial city, max loan ₹10,00,000, conservative approach
- Kolkata: Traditional city, max loan ₹12,00,000, personal loans limited
- Hyderabad: Growing city, max loan ₹15,00,000, startup friendly
- Pune: Educational hub, max loan ₹12,00,000, education loans preferred
- Other cities: Standard policy, max loan ₹10,00,000

Consider:
1. Regional economic conditions
2. Purpose-specific policies
3. Amount reasonableness
4. Market risks

Provide decision in JSON format:
{{
    "policy_decision": "APPROVED/CONDITIONAL/REJECTED",
    "max_allowed_amount": numeric_value,
    "conditions": ["list", "of", "conditions"],
    "reasoning": "detailed explanation",
    "risk_factors": ["list", "of", "risks"],
    "recommendations": ["list", "of", "recommendations"]
}}
"""
                try:
                    policy_result = self.llm._call(policy_prompt)
                    policy_decision = json.loads(policy_result)
                    return json.dumps({
                        "city": city,
                        "purpose": purpose,
                        "requested_amount": amount,
                        **policy_decision
                    }, indent=2)
                except Exception as e:
                    return json.dumps({"error": f"Failed to generate policy decision: {str(e)}"})
                    
            except Exception as e:
                return json.dumps({"error": f"Policy validation error: {str(e)}"})
    
    class RiskAssessmentAgent:
        """Specialized agent for risk assessment with LLM-driven analysis."""
        
        def __init__(self, config=None):
            self.llm = Loan_processing_AI_agent2.GroqLLM(config=config)
    
        def assess_risk(self, query: str) -> str:
            """Perform comprehensive risk assessment with robust parsing."""
            try:
                # Parse the input more carefully
                if '|' not in query:
                    return json.dumps({"error": "Format: user_data_json|loan_amount"})
                
                parts = query.split('|', 1)  # Split only on first |
                user_data_str = parts[0].strip()
                loan_amount_str = parts[1].strip()
                
                # Parse user data
                try:
                    if user_data_str.startswith('{'):
                        user_data = json.loads(user_data_str)
                    else:
                        return json.dumps({"error": "User data must be valid JSON"})
                except json.JSONDecodeError as e:
                    return json.dumps({"error": f"Invalid JSON in user data: {str(e)}"})
                
                # Parse loan amount
                try:
                    loan_amount = float(loan_amount_str)
                except ValueError:
                    return json.dumps({"error": f"Invalid loan amount: {loan_amount_str}"})
                
                # Perform basic risk assessment
                basic_assessment = self._calculate_basic_risk(user_data, loan_amount)
                
                # Try to enhance with LLM analysis
                enhanced_assessment = self._get_llm_risk_analysis(user_data, loan_amount, basic_assessment)
                
                # Combine results
                result = {
                    **basic_assessment,
                    "enhanced_analysis": enhanced_assessment
                }
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                return json.dumps({"error": f"Risk assessment error: {str(e)}"})
        
        def _calculate_basic_risk(self, user_data: dict, loan_amount: float) -> dict:
            """Calculate basic risk assessment using financial ratios."""
            try:
                # Handle nested data structure from DataQuery
                if 'user_data' in user_data:
                    actual_user_data = user_data['user_data']
                else:
                    actual_user_data = user_data
                
                # Extract key metrics with fallbacks
                monthly_salary = actual_user_data.get('monthly_salary', 0)
                existing_emi = actual_user_data.get('existing_emi', 0)
                credit_score = actual_user_data.get('credit_score', 0)
                delayed_payments = actual_user_data.get('delayed_payments', 0)
                
                print(f"[DEBUG] Risk Assessment - Salary: ₹{monthly_salary:,.0f}, Credit: {credit_score}, EMI: ₹{existing_emi:,.0f}")
                
                # Calculate proposed EMI (assuming 5 years = 60 months)
                proposed_emi = loan_amount / 60
                total_emi = existing_emi + proposed_emi
                
                # Calculate ratios
                if monthly_salary > 0:
                    emi_to_income = (total_emi / monthly_salary * 100)
                else:
                    emi_to_income = 999  # Invalid case
                
                # Determine risk level based on actual data
                if credit_score >= 750 and emi_to_income <= 40 and delayed_payments <= 1:
                    risk_grade = "A"
                    risk_category = "Low"
                    decision = "APPROVE"
                elif credit_score >= 700 and emi_to_income <= 50 and delayed_payments <= 2:
                    risk_grade = "B+"
                    risk_category = "Medium"
                    decision = "CONDITIONAL_APPROVE"
                elif credit_score >= 650 and emi_to_income <= 60 and delayed_payments <= 3:
                    risk_grade = "B"
                    risk_category = "Medium"
                    decision = "CONDITIONAL_APPROVE"
                else:
                    risk_grade = "C"
                    risk_category = "High"
                    decision = "REJECT"
                
                # Calculate suggested amount
                if monthly_salary > 0:
                    max_affordable_emi = monthly_salary * 0.4 - existing_emi
                    max_suggested_amount = max_affordable_emi * 60 if max_affordable_emi > 0 else 0
                    suggested_amount = min(loan_amount, max_suggested_amount)
                else:
                    max_affordable_emi = 0
                    suggested_amount = 0
                
                return {
                    "overall_risk_grade": risk_grade,
                    "risk_category": risk_category,
                    "emi_to_income_ratio": round(emi_to_income, 2),
                    "proposed_emi": round(proposed_emi, 2),
                    "total_emi": round(total_emi, 2),
                    "recommendations": {
                        "loan_decision": decision,
                        "suggested_amount": max(0, suggested_amount),
                        "max_affordable_emi": max(0, max_affordable_emi)
                    },
                    "key_metrics": {
                        "credit_score": credit_score,
                        "monthly_salary": monthly_salary,
                        "existing_obligations": existing_emi,
                        "delayed_payments": delayed_payments
                    },
                    "debug_info": {
                        "data_source": "nested" if 'user_data' in user_data else "flat",
                        "parsing_successful": True
                    }
                }
                
            except Exception as e:
                return {
                    "error": f"Basic risk calculation failed: {str(e)}",
                    "debug_info": {
                        "received_data": str(user_data)[:200] + "..." if len(str(user_data)) > 200 else str(user_data)
                    }
                }
        
        def _get_llm_risk_analysis(self, user_data: dict, loan_amount: float, basic_assessment: dict) -> str:
            """Get enhanced LLM analysis with error handling."""
            try:
                prompt = f"""Analyze loan risk:
    Applicant: Credit Score {user_data.get('credit_score', 0)}, Monthly Salary ₹{user_data.get('monthly_salary', 0):,.0f}
    Loan: ₹{loan_amount:,.0f}, EMI Ratio: {basic_assessment.get('emi_to_income_ratio', 0)}%
    Risk Grade: {basic_assessment.get('overall_risk_grade', 'Unknown')}
    
    Provide 2-3 sentences on key risk factors and recommendations."""
                
                return self.llm._call(prompt)
                
            except Exception as e:
                return f"Standard risk assessment applied. Risk grade: {basic_assessment.get('overall_risk_grade', 'Unknown')}"
    
    class UserInteractionAgent:
        """Specialized agent for user interaction with LLM-driven conversation."""
        
        def __init__(self, config=None):
            self.llm = Loan_processing_AI_agent2.GroqLLM(config=config)
    
        def handle_user_input(self, question: str) -> str:
            """Handle user interaction by prompting for actual input."""
            try:
                print(f"[DEBUG] UserInteractionAgent received question: {question}")
                # Print the question to the console and prompt for user input
                print(f"\n🤔 {question}")
                user_response = input("Your response: ").strip()
                
                print(f"[DEBUG] User response: {user_response}")
                if not user_response:
                    return "Please provide a valid response."
                
                return user_response
            except Exception as e:
                print(f"[DEBUG] UserInteraction error: {str(e)}")
                return f"Error processing input: {str(e)}"
    
    class MasterLoanProcessor:
        """Master orchestrator that coordinates all 4 specialized agents."""
        
        def __init__(self, data_manager: 'Loan_processing_AI_agent2.LoanDataManager', config=None):
            self.data_manager = data_manager
            self.config = config
            self.data_agent = Loan_processing_AI_agent2.DataQueryAgent(data_manager, config)
            self.geo_agent = Loan_processing_AI_agent2.GeoPolicyAgent(config)
            self.risk_agent = Loan_processing_AI_agent2.RiskAssessmentAgent(config)
            self.interaction_agent = Loan_processing_AI_agent2.UserInteractionAgent(config)
            self.llm = Loan_processing_AI_agent2.GroqLLM(config=config)
            
            # Create the master coordination agent
            self.master_agent = self._create_master_agent()
    
        def _create_master_agent(self) -> AgentExecutor:
            """Create the master coordination agent."""
            tools = [
                Tool(
                    name="DataQuery",
                    description="Query user data by PAN or Aadhaar. Input: identifier (PAN or Aadhaar number)",
                    func=self.data_agent.query_user_data
                ),
                Tool(
                    name="GeoPolicyCheck",
                    description="Validate geographic policies. Format: 'city:CityName,purpose:loan_purpose,amount:loan_amount'",
                    func=self.geo_agent.validate_geo_policy
                ),
                Tool(
                    name="RiskAssessment",
                    description="Perform risk assessment. Format: 'user_data_json|loan_amount'",
                    func=self.risk_agent.assess_risk
                ),
                Tool(
                    name="UserInteraction",
                    description="Get user input. Input: question to ask the user",
                    func=self.interaction_agent.handle_user_input
                )
            ]
            
            template = """You are a Master Loan Processing Coordinator for an Indian bank.
    
    IMPORTANT: All amounts are in Indian Rupees (₹). Never mention US dollars.
    
    WORKFLOW - Execute systematically:
    1. Get loan purpose and amount from user
    2. Get PAN/Aadhaar from user
    3. Get user's city/location from user (REQUIRED)
    4. Query user data using DataQuery
    5. Check geo-policy using GeoPolicyCheck
    6. Perform risk assessment using RiskAssessment
    7. Make final decision
    
    CRITICAL RULES:
    - ALWAYS ask for user's city - don't assume from data
    - Use tools maximum once each
    - If tool fails, continue with available information
    - If user input is invalid, re-ask the question
    - Do NOT simulate or generate user responses for UserInteraction tool observations
    - Wait for actual user input as provided by the UserInteraction tool
    - When you have enough data, provide final decision immediately
    - Don't use "Action: None" - instead provide Final Answer
    
    Available tools: {tools}
    Tool names: {tool_names}
    
    Question: {input}
    Thought: I need to follow the loan processing workflow step by step
    Action: [tool_name]
    Action Input: [tool_input]
    Observation: [result]
    Thought: [next step or final decision]
    Final Answer: [comprehensive loan decision when ready]
    
    Begin: {agent_scratchpad}"""
    
            prompt = PromptTemplate.from_template(template)
            
            try:
                agent = create_react_agent(self.llm, tools, prompt)
                return AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=True,
                    max_iterations=20,
                    handle_parsing_errors=True,
                    early_stopping_method="classic",
                    callbacks=[DebugCallback()]
                )
            except Exception as e:
                print(f"⚠️ Agent creation failed: {str(e)}")
                return None
    
        def process_application(self, user_input: str) -> str:
            """Process loan application through coordinated multi-agent workflow."""
            print(f"[DEBUG] Starting process_application with input: {user_input}")
            
            if not self.master_agent:
                print("[DEBUG] Master agent not initialized, falling back")
                return self._fallback_processing(user_input, reason="Agent not initialized")
            
            coordination_prompt = f"""
    LOAN APPLICATION REQUEST: "{user_input}"
    
    As the Master Coordinator, process this loan application by:
    
    1. Understanding the user's needs and requirements
    2. Coordinating with specialized agents to gather all necessary information
    3. Ensuring compliance with all policies and regulations
    4. Making a final, well-reasoned lending decision
    
    Coordinate efficiently and provide a comprehensive response.
    """
            
            try:
                print("[DEBUG] Invoking master agent...")
                result = self.master_agent.invoke({"input": coordination_prompt})
                print(f"[DEBUG] Agent result: {result}")
                return result["output"]
                
            except Exception as e:
                print(f"[ERROR] Master agent invocation failed: {str(e)}")
                # Retry once
                try:
                    print("[DEBUG] Retrying master agent invocation...")
                    result = self.master_agent.invoke({"input": coordination_prompt})
                    print(f"[DEBUG] Retry result: {result}")
                    return result["output"]
                except Exception as retry_error:
                    print(f"[ERROR] Retry failed: {retry_error}")
                    return self._fallback_processing(user_input, reason=str(retry_error))
        
        def _fallback_processing(self, user_input: str, reason: str = "Unknown error") -> str:
            """Fallback processing when main agent fails."""
            print(f"[DEBUG] Fallback processing triggered. Reason: {reason}")
            try:
                # Extract loan amount from input
                amount_match = re.search(r'₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs)?', user_input.lower())
                if amount_match:
                    amount_value = float(amount_match.group(1))
                    loan_amount = amount_value * 100000 if 'lakh' in user_input.lower() else amount_value
                else:
                    amount_match = re.search(r'₹?\s*(\d+(?:,\d+)*)', user_input)
                    loan_amount = float(amount_match.group(1).replace(',', '')) if amount_match else 500000
                
                return f"""
🏦 **LOAN APPLICATION ERROR - FALLBACK MODE**

**Error Details:** {reason}
**Requested Input:** {user_input}

📋 **Application Summary:**
• Requested Amount: ₹{loan_amount:,.0f}
• Status: Unable to Process
• Action Required: Please check system configuration (GROQ_API_KEY, dataset, etc.)

⚠️ **Next Steps:**
1. Verify GROQ_API_KEY is set in .env file
2. Ensure Loan_Dataset_V1.csv is accessible
3. Contact technical support if issues persist
4. Resubmit application with:
   - PAN/Aadhaar number
   - City of residence
   - Loan purpose and amount

📞 **Support Contact:**
Please call our helpline or visit a branch for assistance.

**Note:** This is an automated fallback response due to a processing error.
                """
                
            except Exception as e:
                return f"Loan application failed. Error: {str(e)}. Please contact support."
    
    @staticmethod
    def main():
        """Main application entry point."""
        print("=" * 60)
        print("🏦 MULTI-AGENT LOAN PROCESSING SYSTEM")
        print("=" * 60)
        
        try:
            # Initialize system
            config = Loan_processing_AI_agent2.Config()
            data_manager = Loan_processing_AI_agent2.LoanDataManager(config.dataset_path)
            processor = Loan_processing_AI_agent2.MasterLoanProcessor(data_manager, config)
            
            # Get user input
            user_request = input("\n💬 Please describe your loan requirement: ").strip()
            
            if not user_request:
                print("❌ Request cannot be empty")
                return
            
            print(f"\n{'='*60}")
            print("🔄 MULTI-AGENT PROCESSING...")
            print("=" * 60)
            
            # Process application through multi-agent system
            result = processor.process_application(user_request)
            
            print(f"\n{'='*60}")
            print("✅ PROCESSING COMPLETE")
            print("=" * 60)
            print(result)
            
        except Exception as e:
            print(f"❌ System error: {str(e)}")

    @staticmethod
    def process_single_query(user_input: str) -> str:
        """
        Process a single loan query without entering interactive mode.
        This method is used for integration with the main orchestrator.
        """
        print(f"[DEBUG] process_single_query called with: {user_input}")
        try:
            # Initialize system components with proper config
            print("[DEBUG] Initializing config...")
            config = Loan_processing_AI_agent2.Config()
            print("[DEBUG] Initializing data manager...")
            data_manager = Loan_processing_AI_agent2.LoanDataManager(config.dataset_path)
            print("[DEBUG] Initializing processor...")
            processor = Loan_processing_AI_agent2.MasterLoanProcessor(data_manager, config)
            
            # Process the application
            print("[DEBUG] Processing application...")
            result = processor.process_application(user_input)
            print(f"[DEBUG] process_single_query result: {result}")
            return result
            
        except Exception as e:
            print(f"[ERROR] process_single_query failed: {str(e)}")
            # Enhanced fallback processing
            try:
                # Extract loan amount from input
                amount_match = re.search(r'₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs)?', user_input.lower())
                if amount_match:
                    amount_value = float(amount_match.group(1))
                    loan_amount = amount_value * 100000 if 'lakh' in user_input.lower() else amount_value
                else:
                    amount_match = re.search(r'₹?\s*(\d+(?:,\d+)*)', user_input)
                    loan_amount = float(amount_match.group(1).replace(',', '')) if amount_match else 500000
                
                return f"""
🏦 **LOAN APPLICATION ERROR**

**Error Details:** {str(e)}
**Requested Input:** {user_input}

📋 **Application Details:**
• Requested Amount: ₹{loan_amount:,.0f}
• Application ID: LA{datetime.now().strftime('%Y%m%d%H%M%S')}
• Status: Failed

⚠️ **Next Steps:**
1. Verify GROQ_API_KEY is set
2. Check system configuration
3. Resubmit with:
   - PAN/Aadhaar
   - City
   - Loan purpose/amount

📞 **Support:**
Contact our helpline for assistance.
                """
                
            except Exception as fallback_e:
                return f"Loan application failed. Error: {str(fallback_e)}. Please contact support."
    
    @staticmethod
    def get_agent_status() -> Dict[str, Any]:
        """Get the current status of the loan processing agent."""
        try:
            config = Loan_processing_AI_agent2.Config()
            return {
                "agent_type": "Loan_Processing",
                "max_loan_amount": config.max_loan_amount,
                "dataset_path": config.dataset_path,
                "groq_api_available": bool(config.groq_api_key),
                "status": "operational"
            }
        except Exception as e:
            return {
                "agent_type": "Loan_Processing",
                "status": "error",
                "error": str(e)
            }

if __name__ == "__main__":
    Loan_processing_AI_agent2.main()