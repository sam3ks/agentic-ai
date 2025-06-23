from langchain.agents import AgentExecutor, AgentType, initialize_agent, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.schema import AgentAction, AgentFinish
from langchain.agents.agent_types import AgentType
from langchain.agents.react.base import ReActDocstoreAgent
from langchain.callbacks.manager import CallbackManager
from agentic_ai.core.config.loader import LangChainLLMWrapper
from agentic_ai.core.config.logger import DebugCallbackHandler
from agentic_ai.core.config.constants import PROMPT_TEMPLATE_PATH
import os
import sys
import traceback
import json
import re

class CustomReActAgent(ReActDocstoreAgent):
    """A custom ReAct agent that handles parsing errors gracefully."""
    
    def _extract_tool_and_input(self, text: str) -> tuple:
        # Simple regex pattern to extract tool and tool input
        action_match = re.search(r"Action: (.*?)[\n]", text)
        action_input_match = re.search(r"Action Input: (.*)", text)
        
        if not action_match or not action_input_match:
            # Fallback: Try to find any mention of tools in the text
            tools_mentioned = []
            for tool in self.allowed_tools:
                if tool.lower() in text.lower():
                    tools_mentioned.append(tool)
            
            if tools_mentioned:
                # Use the first mentioned tool as default
                return tools_mentioned[0], "default input"
            else:
                # Last resort
                return "UserInteraction", "Please provide more information for your loan application."
        
        action = action_match.group(1).strip()
        action_input = action_input_match.group(1).strip()
        return action, action_input

def create_agent_executor(tools: list) -> AgentExecutor:
    """Creates and returns a simplified AgentExecutor that's guaranteed to work."""
    
    # Initialize the LLM wrapper
    llm = LangChainLLMWrapper()
    llm_type = getattr(llm, "_llm_type", "unknown")
    print(f"✓ Initializing agent with {llm_type.upper()} LLM")
    
    # Define a simple and reliable prompt template with hard-coded sequence
    simple_template = """
You are a Master Loan Processing Coordinator for an Indian bank.

RESPONSE FORMAT: Always use the following format exactly:
Thought: (your detailed reasoning - ALWAYS INCLUDE THIS before each action, with comprehensive analysis)
Action: (the tool name to use, one of: {tool_names})
Action Input: (the input for the tool)
Observation: (the result from the tool)
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: (your final detailed reasoning)
Final Answer: (your final response to the user)

CRITICAL: Your Thought sections MUST be detailed and comprehensive. ALWAYS include your reasoning before EVERY action.
For GeoPolicyCheck and RiskAssessment especially, provide thorough analysis in the Thought section.

MANDATORY REASONING REQUIREMENTS:
1. ALWAYS start with a detailed "Thought:" before EACH action, explaining your decision-making process
2. NEVER skip the "Thought:" section - it is the most important part of your response
3. For GeoPolicyCheck tool: Explain your reasoning about the city, purpose, amount, and how they affect policies
4. For RiskAssessment tool: Analyze the user's financial situation, discussing DTI ratio, credit score implications, and overall risk factors
5. Include ALL intermediate reasoning, not just final conclusions
6. Use detailed, specific assessments rather than generic statements

MANDATORY SEQUENCE - DO NOT SKIP ANY STEP:
1. UserInteraction to ask for loan purpose: "What is the purpose of your loan?"
2. UserInteraction to ask for loan amount: "How much loan amount do you need?"
3. UserInteraction to ask for PAN/Aadhaar: "Please provide your PAN or Aadhaar number."
4. DataQuery with the PAN/Aadhaar
5. UserInteraction to ask for city: "Please provide your city or location."
6. GeoPolicyCheck with format: city:CITY,purpose:PURPOSE,amount:AMOUNT
7. RiskAssessment with format: user_data_json|loan_amount
8. Final decision based on both assessments

TOOLS AVAILABLE:
{tools}

TASK:
{input}

{agent_scratchpad}
"""
    
    # Create a prompt template with all required variables
    prompt = PromptTemplate(
        input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
        template=simple_template
    )
    
    try:
        # Create a custom agent directly - most reliable approach
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        
        # Create a custom callback handler and manager
        debug_handler = DebugCallbackHandler()
        callback_manager = CallbackManager(handlers=[debug_handler])
        
        # Create the agent executor with explicit callback manager to show reasoning
        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            verbose=True,  # Set to True to allow full logging of intermediate steps
            handle_parsing_errors=True,
            max_iterations=15,
            early_stopping_method="generate",
            callback_manager=callback_manager,
            return_intermediate_steps=True  # Important: return all intermediate steps for logging
        )
        return agent_executor
    
    except Exception as e:
        print(f"⚠️ Agent creation failed: {str(e)}")
        print("Detailed error:", traceback.format_exc())
        
        # Ultimate fallback - extremely simplified
        try:
            # Create a custom callback handler and manager
            debug_handler = DebugCallbackHandler()
            callback_manager = CallbackManager(handlers=[debug_handler])
            
            # Try one last approach with initialize_agent
            agent_executor = initialize_agent(
                tools=tools,
                llm=llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # Simplest agent type
                verbose=True,  # Set to True to allow full logging of intermediate steps
                handle_parsing_errors=True,
                callback_manager=callback_manager,
                return_intermediate_steps=True  # Important: return all intermediate steps for logging
            )
            return agent_executor
        except Exception as e2:
            print(f"⚠️ All agent creation methods failed: {str(e2)}")
            return None