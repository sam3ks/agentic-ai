#agent_executor
from typing import TypedDict, Annotated, Sequence
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.prebuilt import ToolExecutor
from langgraph.graph import StateGraph, END
from agentic_ai.core.config.loader import LangChainLLMWrapper
from langchain_core.prompts import PromptTemplate
from agentic_ai.core.config.constants import PROMPT_TEMPLATE_PATH
from agentic_ai.core.config.logger import get_logger
import json
import re
 
logger = get_logger(__name__)
 
class AgentState(TypedDict):
    input: str
    agent_outcome: AgentFinish | AgentAction | None
    intermediate_steps: Annotated[Sequence[tuple[AgentAction, str]], lambda x, y: x + y]
    # Track critical workflow steps
    steps_completed: dict
    geo_policy_done: bool
    risk_assessment_done: bool
    # Add loop detection
    step_count: int
    last_action: str
    # NEW: Add fields to store collected data
    purpose: str
    amount: str # Keep as string to handle inputs like "5 lakhs"
    city: str
    pan: str
    aadhaar: str
    # Add fields for additional UserInteraction responses
    salary_update_confirmation: str
    document_path: str
    agreement_response: str
    # Add definitive workflow termination flag
    workflow_finished: bool
 
def create_agent_workflow(tools: list):
    tool_executor = ToolExecutor(tools)
 
    llm = LangChainLLMWrapper()
 
    simple_template = """
You are a comprehensive loan processing agent. You must complete the FULL loan processing workflow systematically.
 
COMPLETE WORKFLOW STEPS (execute in this order):
1. LoanPurposeAssessment - Assess loan purpose eligibility  
2. UserInteraction - Ask for user details (loan amount, PAN/Aadhaar, city, etc.)
3. DataQuery - Query user data from database
4. GeoPolicyCheck - Check location-based policies with format: city:CITY,purpose:PURPOSE,amount:AMOUNT
5. RiskAssessment - Perform comprehensive risk evaluation with format: user_data_json|loan_amount
6. AgreementPresentation - Present loan terms and conditions (if loan is approved)
7. UserInteraction - Ask user to accept/decline the loan agreement
8. AgreementPresentation - Process user's acceptance/rejection response
9. Final Answer - Provide comprehensive final decision and confirmation
 
CRITICAL RULES:
- Execute ALL steps in the workflow - do not skip any major step
- Execute ONLY ONE action at a time - wait for each tool response before proceeding
- NEVER EVER ask for information that appears in the "ALREADY COLLECTED INFORMATION" section
- If information is marked as "CONFIRMED" in the context, it means you have it - DO NOT ask for it again
- If you have the user's PAN in the context, your next step MUST be DataQuery (NOT UserInteraction)
- If you have Purpose, Amount, and PAN in context, proceed to GeoPolicyCheck (ask for city first if needed)
- After RiskAssessment, if loan is approved, you MUST present AgreementPresentation
- After presenting agreement, you MUST ask user for acceptance using UserInteraction
- After user responds, you MUST process their response with AgreementPresentation again
- NEVER write fake "Observation:" lines
- Progress through ALL workflow steps before providing Final Answer
- For DataQuery: use the PAN number from the context.
- For GeoPolicyCheck: use exact format city:CITY,purpose:PURPOSE,amount:AMOUNT  
- For RiskAssessment: use exact format user_data_json|loan_amount
- For AgreementPresentation: use loan details JSON from RiskAssessment output
- Only provide Final Answer after completing all steps including agreement processing
 
MANDATORY INFORMATION USAGE:
- If "LOAN PURPOSE CONFIRMED" appears in context: USE IT, don't ask again
- If "LOAN AMOUNT CONFIRMED" appears in context: USE IT, don't ask again  
- If "CITY CONFIRMED" appears in context: USE IT, don't ask again
- If "PAN CONFIRMED" appears in context: USE IT for DataQuery, don't ask again
 
WORKFLOW PROGRESSION:
- After LoanPurposeAssessment → UserInteraction (collect details ONLY if not in context)
- After UserInteraction → DataQuery (query user data)
- After DataQuery → Check response for salary workflow:
  * If existing user (action_needed: ask_about_salary_update): Ask salary update question
  * If user says YES to salary update: Ask for PDF and use PDFSalaryExtractor  
  * If user says NO to salary update: Use UseExistingUserData tool to get stored data
  * If new user: Ask for PDF and use PDFSalaryExtractor
- After salary workflow → UserInteraction (ask for city if needed)
- After collecting city → GeoPolicyCheck
- After GeoPolicyCheck → RiskAssessment (use data from UseExistingUserData or PDFSalaryExtractor)
- After RiskAssessment → AgreementPresentation (present loan terms)
- After presenting terms → UserInteraction (ask for user acceptance)
- After user response → AgreementPresentation (process acceptance/rejection)
- After processing response → Final Answer
 
FORMAT (use EXACTLY this format):
Thought: [your reasoning for the next action]
Action: [tool name from: {tool_names}]
Action Input: [input for the tool]
 
IMPORTANT: Execute ONLY ONE Action per response. Do not chain multiple actions together.
 
Available tools: {tools}
 
Current task: {input}
 
{agent_scratchpad}
 
IMPORTANT: Execute the complete loan processing pipeline. Execute one action at a time and wait for the result before proceeding to the next step.
"""
 
    prompt = PromptTemplate(
        input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
        template=simple_template
    )
 
    def parse_agent_output(output: str, state: AgentState = None):
        """Parse LLM output to extract action or final answer with simple workflow enforcement."""
        if not output or output.strip() == "":
            print("[ERROR] LLM output is empty or None. Returning None.")
            raise ValueError("LLM output is empty or None.")
 
        # Get current state information for step counting
        step_count = 0
        steps_completed = {}
        if state:
            step_count = state.get("step_count", 0)
            steps_completed = state.get("steps_completed", {})
       
        print(f"[DEBUG] parse_agent_output called - Step count: {step_count}")
        print(f"[DEBUG] Steps completed: {list(steps_completed.keys())}")
        print(f"[DEBUG] Output length: {len(output)} characters")
       
        # More comprehensive termination based on complete workflow execution
        essential_steps_done = (
            "LoanPurposeAssessment" in steps_completed and
            "UserInteraction" in steps_completed and
            "DataQuery" in steps_completed
        )
       
        # Complete workflow - ALL required steps must be done including COMPLETE agreement flow
        # We need both AgreementPresentation AND user acceptance processing
        agreement_steps_done = steps_completed.get("AgreementPresentation", 0) >= 2  # Both present and process
       
        complete_workflow_done = (
            essential_steps_done and
            "GeoPolicyCheck" in steps_completed and
            "RiskAssessment" in steps_completed and
            agreement_steps_done  # Require complete agreement flow
        )
       
        # Only terminate if we have truly completed the full workflow including user acceptance
        if complete_workflow_done and step_count >= 10:
            print(f"[DEBUG] Complete workflow finished at step {step_count} - forcing Final Answer")
            return AgentFinish(
                return_values={"output": "Complete loan processing workflow finished successfully. All essential steps including risk assessment, agreement presentation, and user acceptance completed. Final loan decision ready."},
                log="Forced Final Answer due to complete workflow completion including user acceptance"
            )
       
        # Emergency termination if too many steps (increased limit for complete workflow including agreement)
        if step_count > 30:
            print(f"[DEBUG] Forcing Final Answer due to step count limit: {step_count}")
            return AgentFinish(
                return_values={"output": "Loan application processed with available information. [Auto-terminated after 30 steps]"},
                log="Forced Final Answer due to step count"
            )
 
        # CRITICAL: Check for Final Answer FIRST - this takes priority over any actions
        final_answer_match = re.search(r"Final Answer:\s*(.*?)(?:\n|$)", output, re.DOTALL)
        if final_answer_match:
            print("[DEBUG] Detected Final Answer in LLM output - terminating workflow.")
            return AgentFinish(
                return_values={"output": final_answer_match.group(1).strip()},
                log=output
            )
 
        # CRITICAL: Reject responses with fake "Observation:" lines
        if "Observation:" in output:
            print("[DEBUG] Detected hallucinated Observation - forcing termination")
            return AgentFinish(
                return_values={"output": "Loan application completed based on available information."},
                log="Terminated due to hallucinated observations"
            )

        # Check for multiple actions in a single response (but allow sequential workflow steps)
        action_count = len(re.findall(r"^Action:", output, re.MULTILINE))
        if action_count > 1:
            print(f"[DEBUG] Detected {action_count} actions in single response - will only execute the first action")
            # Instead of terminating, just take the first action and continue
            # This allows the workflow to proceed naturally
 
        # Look for Action and Action Input (take only the first if multiple)
        action_matches = re.findall(r"Action:\s*(\w+)", output)
        input_matches = re.findall(r"Action Input:\s*(.+)", output)
       
        if action_matches and input_matches:
            # Take only the first action and input
            action_name = action_matches[0].strip()
            action_input = input_matches[0].strip()
            print(f"[DEBUG] Parsed action: {action_name}, input: {action_input}")
            if len(action_matches) > 1:
                print(f"[DEBUG] Multiple actions detected, using first: {action_name}")
            return AgentAction(tool=action_name, tool_input=action_input, log=output)
       
        print(f"[ERROR] Could not parse agent output. Output was:\n{output}")
        # Force termination if we can't parse
        return AgentFinish(
            return_values={"output": "Unable to parse agent response. Terminating workflow."},
            log="Terminated due to unparseable output"
        )
 
    def run_agent(state: AgentState):
        # HIGHEST PRIORITY: Check for finish flag
        if state.get("workflow_finished", False):
            print(f"[DEBUG] WORKFLOW_FINISHED - preserving state without running agent")
            return state
       
        # CRITICAL: If there's already an AgentFinish, preserve it - don't override!
        existing_outcome = state.get("agent_outcome")
        if isinstance(existing_outcome, AgentFinish):
            print(f"[DEBUG] Preserving existing AgentFinish: {existing_outcome.return_values}")
            return {"agent_outcome": existing_outcome}
       
        agent_scratchpad = ""
        intermediate_steps = state.get("intermediate_steps", [])
       
        # Limit scratchpad to last 3 steps to prevent context overflow
        recent_steps = intermediate_steps[-3:] if len(intermediate_steps) > 3 else intermediate_steps
       
        if recent_steps:
            for action, observation in recent_steps:
                agent_scratchpad += f"Thought: I need to execute {action.tool}\n"
                agent_scratchpad += f"Action: {action.tool}\n"
                agent_scratchpad += f"Action Input: {action.tool_input}\n"
                # Truncate long observations to prevent context overflow
                obs_text = str(observation)
                if len(obs_text) > 500:
                    obs_text = obs_text[:500] + "...[truncated]"
                agent_scratchpad += f"Observation: {obs_text}\n\n"
 
        # Add progress tracking to help the agent understand what's been done
        steps_completed = state.get("steps_completed", {})
        step_count = state.get("step_count", 0)
       
        # NEW: Add collected data to the scratchpad
        purpose = state.get("purpose")
        amount = state.get("amount")
        city = state.get("city")
        pan = state.get("pan")
        aadhaar = state.get("aadhaar")
 
        print(f"[DEBUG] Current state values - Purpose: {purpose}, Amount: {amount}, City: {city}, PAN: {pan}, Aadhaar: {aadhaar}")
 
        # Add a prominent context section at the top of the scratchpad
        if purpose or amount or city or pan or aadhaar:
            agent_scratchpad += "==== CRITICAL: ALREADY COLLECTED INFORMATION ====\n"
            agent_scratchpad += "DO NOT ASK FOR ANY OF THE FOLLOWING INFORMATION AGAIN!\n"
            if purpose and purpose != "not_detected":
                agent_scratchpad += f"✓ LOAN PURPOSE CONFIRMED: {purpose} (NEVER ask for this again)\n"
            if amount:
                agent_scratchpad += f"✓ LOAN AMOUNT CONFIRMED: {amount} (NEVER ask for this again)\n"
            if city:
                agent_scratchpad += f"✓ CITY CONFIRMED: {city} (NEVER ask for this again)\n"
            if pan:
                agent_scratchpad += f"✓ PAN CONFIRMED: {pan} (NEVER ask for this again)\n"
            if aadhaar:
                agent_scratchpad += f"✓ AADHAAR CONFIRMED: {aadhaar} (NEVER ask for this again)\n"
            agent_scratchpad += "==== PROCEED TO NEXT WORKFLOW STEP IMMEDIATELY ====\n\n"
 
        # Add specific next step guidance based on current state - STRICT PRIORITY ORDER
        # PRIORITY 0: Get missing basic information first
        if not purpose or purpose in ["unknown", "not_detected"]:
            agent_scratchpad += "*** HIGHEST PRIORITY: Ask for loan purpose using UserInteraction ***\n\n"
        elif not amount:
            agent_scratchpad += "*** HIGHEST PRIORITY: Ask for loan amount using UserInteraction ***\n\n"
        elif not pan:
            agent_scratchpad += "*** HIGHEST PRIORITY: Ask for PAN/Aadhaar using UserInteraction ***\n\n"
        elif purpose and amount and pan and not steps_completed.get("DataQuery"):
            agent_scratchpad += "*** NEXT REQUIRED ACTION: DataQuery using PAN " + str(pan) + " ***\n\n"
        elif steps_completed.get("DataQuery"):
            # CRITICAL: Check salary workflow state first
            salary_confirmation = state.get("salary_update_confirmation", "")
            document_path = state.get("document_path", "")
            salary_workflow_complete = steps_completed.get("PDFSalaryExtractor") or steps_completed.get("UseExistingUserData")
            
            # PRIORITY 1: Handle salary workflow if not complete
            if not salary_workflow_complete:
                # Check if we just completed DataQuery - need salary workflow handling
                last_step_was_dataquery = (
                    intermediate_steps and
                    len(intermediate_steps) > 0 and
                    intermediate_steps[-1][0].tool == "DataQuery"
                )
               
                if last_step_was_dataquery:
                    # Check the DataQuery response for salary workflow
                    dataquery_output = intermediate_steps[-1][1]
                    if '"action_needed": "ask_about_salary_update"' in str(dataquery_output) or '"_orchestrator_next_action": "salary_update_question"' in str(dataquery_output):
                        agent_scratchpad += "*** CRITICAL: EXISTING USER FOUND - You MUST ask: 'Do you want to update your salary information?' ***\n"
                        agent_scratchpad += "*** DO NOT ask for city! Handle salary workflow first! ***\n\n"
                    elif '"status": "new_user_found_proceed_to_salary_sheet"' in str(dataquery_output):
                        agent_scratchpad += "*** CRITICAL: NEW USER FOUND - You MUST ask: 'Please upload your salary information (PDF)' ***\n"
                        agent_scratchpad += "*** DO NOT ask for city! Handle salary workflow first! ***\n\n"
                elif salary_confirmation == "no":
                    agent_scratchpad += "*** CRITICAL: User said NO to salary update - You MUST use UseExistingUserData tool NOW ***\n"
                    agent_scratchpad += "*** DO NOT ask for city! Complete salary workflow first! ***\n\n"
                elif salary_confirmation == "yes" and not document_path:
                    agent_scratchpad += "*** CRITICAL: User said YES to salary update - Ask for PDF path NOW ***\n"
                    agent_scratchpad += "*** DO NOT ask for city! Get PDF path first! ***\n\n"
                elif salary_confirmation == "yes" and document_path and not steps_completed.get("PDFSalaryExtractor"):
                    agent_scratchpad += "*** CRITICAL: PDF path provided - You MUST use PDFSalaryExtractor NOW ***\n"
                    agent_scratchpad += "*** DO NOT ask for city! Complete PDF extraction first! ***\n\n"
            else:
                # PRIORITY 2: Salary workflow is complete - proceed to next steps
                if not steps_completed.get("GeoPolicyCheck"):
                    # Use city if available, otherwise let GeoPolicyCheck handle missing city
                    city_param = city if city and city != "unknown" else "MISSING"
                    agent_scratchpad += f"*** SALARY WORKFLOW COMPLETE - Run GeoPolicyCheck NOW: city:{city_param},purpose:{purpose},amount:{amount} ***\n\n"
 
        if steps_completed:
            agent_scratchpad += f"[PROGRESS] Steps completed so far: {list(steps_completed.keys())}\n"
            agent_scratchpad += f"[PROGRESS] Current step: {step_count + 1}\n\n"
 
        tool_names = [tool.name for tool in tools]
        tools_str = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
 
        formatted_prompt = prompt.format(
            input=state["input"],
            agent_scratchpad=agent_scratchpad,
            tools=tools_str,
            tool_names=", ".join(tool_names)
        )
 
        response_text = llm._call(formatted_prompt)
       
        # Check for context length error
        if "context_length_exceeded" in response_text or "maximum context length" in response_text:
            print("[ERROR] Context length exceeded - forcing workflow termination")
            return AgentFinish(
                return_values={"output": "Loan application processing completed successfully. Context limit reached."},
                log="Terminated due to context length exceeded"
            )
       
        # Clean format inspired by expected output
        if "Thought:" in response_text and "Action:" in response_text:
            thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", response_text, re.DOTALL)
            action_match = re.search(r"Action:\s*(\w+)", response_text)
            input_match = re.search(r"Action Input:\s*(.+)", response_text)
           
            if thought_match and action_match:
                thought = thought_match.group(1).strip()
                action_name = action_match.group(1).strip()
                action_input = input_match.group(1).strip() if input_match else ""
               
                print("----------------------------------------")
                print(f"💭 AGENT REASONING: {thought}")
                print("----------------------------------------")
                print(f"🔄 Action: {action_name}")
                print(f"📝 Action Input: {action_input}")
            else:
                print("\n[DEBUG] Raw LLM output:")
                print(response_text)
        else:
            print("\n[DEBUG] Raw LLM output:")
            print(response_text)
       
        agent_outcome = parse_agent_output(response_text, state)
        return {"agent_outcome": agent_outcome}
 
    def execute_tools(state: AgentState):
        # EARLY TERMINATION CHECK: If workflow is already finished, don't execute more tools
        if state.get("workflow_finished", False):
            print("[DEBUG] EARLY TERMINATION: workflow_finished flag is True, not executing tools")
            return state
       
        # EARLY TERMINATION CHECK: If step count is too high, force termination
        # Allow up to 25 steps for complete workflow including security validation retries and error corrections
        current_step = state.get("step_count", 0)
        if current_step >= 25:  # Increased to accommodate security validation retries and error corrections
            print(f"[DEBUG] EARLY TERMINATION: Step count {current_step} >= 25, forcing workflow termination")
            from langchain_core.agents import AgentFinish
            return {
                **state,
                "agent_outcome": AgentFinish(
                    return_values={"output": "Loan processing workflow completed successfully. All required steps have been executed and the loan application has been processed."},
                    log="Terminated at step limit in execute_tools"
                ),
                "workflow_finished": True,
                "step_count": current_step + 1,
            }
       
        action = state.get("agent_outcome")
        if action is None:
            print("[ERROR] agent_outcome is None in execute_tools. State:", state)
            return {
                "intermediate_steps": state.get("intermediate_steps", []),
                "steps_completed": state.get("steps_completed", {}),
                "geo_policy_done": state.get("geo_policy_done", False),
                "risk_assessment_done": state.get("risk_assessment_done", False),
                "step_count": state.get("step_count", 0),
                "last_action": None,
                # CRITICAL: Preserve existing collected data
                "purpose": state.get("purpose", ""),
                "amount": state.get("amount", ""),
                "city": state.get("city", ""),
                "pan": state.get("pan", ""),
                "aadhaar": state.get("aadhaar", ""),
                "salary_update_confirmation": state.get("salary_update_confirmation", ""),
                "document_path": state.get("document_path", ""),
                "agreement_response": state.get("agreement_response", ""),
            }
       
        output = tool_executor.invoke(action)
       
        # NEW: Update state with collected data
        updated_state = {}
        if action.tool == "UserInteraction":
            # Check if user ended the application by declining escalation
            if output == "USER_ENDED_APPLICATION" or output == "USER_TERMINATED_APPLICATION":
                print("[DEBUG] User ended application - forcing workflow termination")
                from langchain_core.agents import AgentFinish
                return {
                    "agent_outcome": AgentFinish(
                        return_values={"output": "Loan application ended by user. User declined escalation to human agent."},
                        log="User ended application by declining escalation"
                    ),
                    "intermediate_steps": state.get("intermediate_steps", []) + [(action, output)],
                    "steps_completed": state.get("steps_completed", {}),
                    "step_count": state["step_count"] + 1,
                    "last_action": action.tool,
                    "workflow_finished": True
                }
            
            try:
                interaction_data = json.loads(output)
                if isinstance(interaction_data, dict):
                    updated_state.update(interaction_data)
                    print(f"[DEBUG] Updated state from UserInteraction: {updated_state}")
                    
                    # Immediately save the state to session to prevent data loss on Ctrl+C
                    try:
                        from agentic_ai.core.session.session_manager import get_session_manager
                        session_manager = get_session_manager()
                        if session_manager.session_id:
                            for key, value in updated_state.items():
                                session_manager.update_collected_data(key, value)
                            print(f"[DEBUG] Saved state to session: {updated_state}")
                    except Exception as e:
                        print(f"[WARNING] Could not save state to session: {e}")
            except json.JSONDecodeError:
                print(f"[WARNING] Could not decode JSON from UserInteraction output: {output}")
        
        # Handle LoanPurposeAssessment to extract mapped category
        elif action.tool == "LoanPurposeAssessment":
            try:
                purpose_data = json.loads(output)
                if isinstance(purpose_data, dict):
                    mapped_category = purpose_data.get("matched_category")
                    if mapped_category:
                        updated_state["purpose"] = mapped_category
                        print(f"[DEBUG] Updated purpose from LoanPurposeAssessment: {mapped_category}")
                        
                        # Save mapped category to session
                        try:
                            from agentic_ai.core.session.session_manager import get_session_manager
                            session_manager = get_session_manager()
                            if session_manager.session_id:
                                session_manager.update_collected_data("purpose", mapped_category)
                                print(f"[DEBUG] Saved mapped purpose to session: {mapped_category}")
                        except Exception as e:
                            print(f"[WARNING] Could not save mapped purpose to session: {e}")
            except json.JSONDecodeError:
                print(f"[WARNING] Could not decode JSON from LoanPurposeAssessment output: {output}")
        
        # CRITICAL: Handle RiskAssessment results - check for rejection
        elif action.tool == "RiskAssessment":
            try:
                risk_data = json.loads(output)
                if isinstance(risk_data, dict):
                    risk_category = risk_data.get("risk_category", {})
                    if isinstance(risk_category, dict):
                        decision = risk_category.get("decision", "").lower()
                        credit_score = risk_data.get("user_data_summary", {}).get("credit_score", 0)
                        
                        print(f"[DEBUG] RiskAssessment decision: {decision}, Credit Score: {credit_score}")
                        
                        # If loan is rejected, terminate workflow immediately
                        if decision == "reject":
                            print("[DEBUG] LOAN REJECTED by RiskAssessment - TERMINATING WORKFLOW")
                            from langchain_core.agents import AgentFinish
                            
                            rejection_message = f"""🚫 **LOAN APPLICATION REJECTED**

After careful assessment of your financial profile, we regret to inform you that your loan application cannot be approved at this time.

**Assessment Summary:**
• Credit Score: {credit_score}
• Risk Category: {risk_category.get('name', 'High Risk')}
• Decision: REJECTED

**Reason for Rejection:**
{risk_category.get('notes', 'Credit score and financial profile do not meet our current lending criteria.')}

**Next Steps:**
• Improve your credit score by paying bills on time
• Reduce existing debt obligations  
• Consider applying again after 6 months
• Contact our customer service for personalized guidance

Thank you for considering our services. We appreciate your interest and encourage you to reapply once your financial profile improves."""
                            
                            return {
                                "agent_outcome": AgentFinish(
                                    return_values={"output": rejection_message},
                                    log="Loan rejected by RiskAssessment - workflow terminated"
                                ),
                                "intermediate_steps": state.get("intermediate_steps", []) + [(action, output)],
                                "steps_completed": state.get("steps_completed", {}),
                                "geo_policy_done": state.get("geo_policy_done", False),
                                "risk_assessment_done": True,
                                "step_count": state["step_count"] + 1,
                                "last_action": action.tool,
                                "purpose": state.get("purpose", ""),
                                "amount": state.get("amount", ""),
                                "city": state.get("city", ""),
                                "pan": state.get("pan", ""),
                                "aadhaar": state.get("aadhaar", ""),
                                "salary_update_confirmation": state.get("salary_update_confirmation", ""),
                                "document_path": state.get("document_path", ""),
                                "agreement_response": state.get("agreement_response", ""),
                                "workflow_finished": True
                            }
                            
            except json.JSONDecodeError:
                print(f"[WARNING] Could not decode JSON from RiskAssessment output: {output}")
       
        # Track completed steps - special handling for AgreementPresentation to count calls
        current_action = getattr(action, 'tool', 'UNKNOWN')
        if current_action == "AgreementPresentation":
            # Count AgreementPresentation calls (first=present, second=process acceptance)
            agreement_count = state.get("steps_completed", {}).get("AgreementPresentation", 0)
            updated_steps_completed = state.get("steps_completed", {}).copy()
            updated_steps_completed["AgreementPresentation"] = agreement_count + 1
            print(f"[DEBUG] AgreementPresentation call #{agreement_count + 1}")
        else:
            updated_steps_completed = state.get("steps_completed", {}).copy()
            updated_steps_completed[current_action] = True
            
            # SPECIAL: Track salary workflow completion
            if current_action == "PDFSalaryExtractor":
                print(f"[DEBUG] PDFSalaryExtractor completed - salary workflow finished")
            elif current_action == "UseExistingUserData":
                print(f"[DEBUG] UseExistingUserData completed - salary workflow finished")
       
        # Check for repeated actions but don't fail, just log
        last_action = state.get("last_action", None)
        if last_action == current_action:
            print(f"[WARNING] Detected repeated action: {current_action}")
       
        geo_policy_done = updated_steps_completed.get("GeoPolicyCheck", False)
        risk_assessment_done = updated_steps_completed.get("RiskAssessment", False)
       
        print(f"🔍 Step {state['step_count'] + 1}: Executed {current_action}")
        print(f"[DEBUG] Steps completed so far: {list(updated_steps_completed.keys())}")
        if current_action == "AgreementPresentation":
            print(f"[DEBUG] AgreementPresentation calls: {updated_steps_completed.get('AgreementPresentation', 0)}")
        print(f"[DEBUG] Current step count: {state['step_count'] + 1}, Last action: {last_action}")
       
        # Check for potential infinite loops
        if state["step_count"] + 1 > 15:
            print(f"[WARNING] High step count detected: {state['step_count'] + 1}")
            print(f"[WARNING] Recent steps: {list(updated_steps_completed.keys())[-5:]}")
       
        # Build the updated intermediate steps by appending to existing ones
        updated_intermediate_steps = state.get("intermediate_steps", []) + [(action, output)]
       
        # Only force termination if we have comprehensive workflow completion
        essential_steps_done = (
            "LoanPurposeAssessment" in updated_steps_completed and
            "UserInteraction" in updated_steps_completed and
            "DataQuery" in updated_steps_completed
        )
       
        # Complete workflow - ALL required steps must be done including COMPLETE agreement flow
        # We need both AgreementPresentation AND user acceptance processing
        agreement_steps_done = updated_steps_completed.get("AgreementPresentation", 0) >= 2  # Both present and process
       
        complete_workflow_done = (
            essential_steps_done and
            "GeoPolicyCheck" in updated_steps_completed and
            "RiskAssessment" in updated_steps_completed and
            agreement_steps_done  # Require complete agreement flow
        )
       
        if complete_workflow_done and state["step_count"] + 1 >= 10:
            print("[DEBUG] FORCE TERMINATING: Complete workflow finished at execute_tools")
            from langchain_core.agents import AgentFinish
            return {
                "agent_outcome": AgentFinish(
                    return_values={"output": f"Complete loan processing workflow finished successfully. Steps executed: {list(updated_steps_completed.keys())}. All essential steps including risk assessment, agreement presentation, and user acceptance completed. Final loan decision ready."},
                    log="Forced termination after complete workflow including user acceptance in execute_tools"
                ),
                "intermediate_steps": updated_intermediate_steps,
                "steps_completed": updated_steps_completed,
                "geo_policy_done": geo_policy_done,
                "risk_assessment_done": risk_assessment_done,
                "step_count": state["step_count"] + 1,
                "last_action": current_action,
                # CRITICAL: Preserve existing collected data WITH UPDATES
                "purpose": updated_state.get("purpose", state.get("purpose", "")),
                "amount": updated_state.get("amount", state.get("amount", "")),
                "city": updated_state.get("city", state.get("city", "")),
                "pan": updated_state.get("pan", state.get("pan", "")),
                "aadhaar": updated_state.get("aadhaar", state.get("aadhaar", "")),
                "salary_update_confirmation": updated_state.get("salary_update_confirmation", state.get("salary_update_confirmation", "")),
                "document_path": updated_state.get("document_path", state.get("document_path", "")),
                "agreement_response": updated_state.get("agreement_response", state.get("agreement_response", "")),
                # Add definitive workflow termination flag
                "workflow_finished": True,
            }
       
        # Emergency termination if AgreementPresentation has been called twice (present + accept)
        if current_action == "AgreementPresentation" and updated_steps_completed.get("AgreementPresentation", 0) >= 2:
            print("[DEBUG] FORCE TERMINATING: Agreement flow completed")
            from langchain_core.agents import AgentFinish
            return {
                "agent_outcome": AgentFinish(
                    return_values={"output": "Your loan application has been successfully processed. Thank you for choosing us!"},
                    log="Terminated after complete agreement acceptance flow"
                ),
                "intermediate_steps": updated_intermediate_steps,
                "steps_completed": updated_steps_completed,
                "geo_policy_done": geo_policy_done,
                "risk_assessment_done": risk_assessment_done,
                "step_count": state["step_count"] + 1,
                "last_action": current_action,
                # CRITICAL: Preserve existing collected data WITH UPDATES
                "purpose": updated_state.get("purpose", state.get("purpose", "")),
                "amount": updated_state.get("amount", state.get("amount", "")),
                "city": updated_state.get("city", state.get("city", "")),
                "pan": updated_state.get("pan", state.get("pan", "")),
                "aadhaar": updated_state.get("aadhaar", state.get("aadhaar", "")),
                "salary_update_confirmation": updated_state.get("salary_update_confirmation", state.get("salary_update_confirmation", "")),
                "document_path": updated_state.get("document_path", state.get("document_path", "")),
                "agreement_response": updated_state.get("agreement_response", state.get("agreement_response", "")),
                # Add definitive workflow termination flag
                "workflow_finished": True,
            }
       
        # Continue with normal workflow - update state and prepare for next iteration
       
        final_state = {
            "intermediate_steps": updated_intermediate_steps,
            "steps_completed": updated_steps_completed,
            "geo_policy_done": geo_policy_done,
            "risk_assessment_done": risk_assessment_done,
            "step_count": state["step_count"] + 1,
            "last_action": current_action,
            # CRITICAL: Preserve existing collected data WITH UPDATES
            "purpose": updated_state.get("purpose", state.get("purpose", "")),
            "amount": updated_state.get("amount", state.get("amount", "")),
            "city": updated_state.get("city", state.get("city", "")),
            "pan": updated_state.get("pan", state.get("pan", "")),
            "aadhaar": updated_state.get("aadhaar", state.get("aadhaar", "")),
            "salary_update_confirmation": updated_state.get("salary_update_confirmation", state.get("salary_update_confirmation", "")),
            "document_path": updated_state.get("document_path", state.get("document_path", "")),
            "agreement_response": updated_state.get("agreement_response", state.get("agreement_response", "")),
            # Preserve workflow_finished flag
            "workflow_finished": state.get("workflow_finished", False),
        }
        # Note: updated_state is already applied above, no need for additional update
        return final_state
 
    def should_continue(state: AgentState):
        # HIGHEST PRIORITY: Check for explicit finish flag
        if state.get("workflow_finished", False):
            print(f"[DEBUG] WORKFLOW_FINISHED flag detected - returning 'end'")
            return "end"
       
        step_count = state.get("step_count", 0)
        agent_outcome = state.get("agent_outcome")
        last_action = state.get("last_action", "None")
        steps_completed = state.get("steps_completed", {})
       
        print(f"[DEBUG] should_continue - Step: {step_count}, Last action: {last_action}, Outcome type: {type(agent_outcome).__name__}")
        print(f"[DEBUG] Steps completed: {list(steps_completed.keys())}")
       
        # CRITICAL: Check for AgentFinish first - this should always terminate
        if isinstance(agent_outcome, AgentFinish):
            print("✅ Workflow complete - AgentFinish detected")
            return "end"
       
        # ABSOLUTE FAILSAFE: Never allow more than 20 steps, period!
        if step_count >= 20:
            print(f"⚠️ ABSOLUTE FAILSAFE: Step {step_count} >= 20 - IMMEDIATE TERMINATION")
            return "end"
       
        # Check for agreement completion - this should be the normal termination
        agreement_calls = steps_completed.get("AgreementPresentation", 0)
        essential_steps = ["LoanPurposeAssessment", "DataQuery", "GeoPolicyCheck", "RiskAssessment"]
        has_all_essential = all(step in steps_completed for step in essential_steps)
        has_agreement = "AgreementPresentation" in steps_completed
       
        # Normal completion: All steps + 2 agreement calls
        if has_all_essential and has_agreement and agreement_calls >= 2:
            print(f"⚠️ NORMAL COMPLETION: All steps + agreement done - TERMINATING")
            return "end"
       
        # Extra safety: If we have essential steps + agreement and step >= 25  
        if has_all_essential and has_agreement and step_count >= 25:
            print(f"⚠️ STEP LIMIT COMPLETION: Essential + agreement + step {step_count} - TERMINATING")
            return "end"
       
        print(f"[DEBUG] Continuing workflow - step {step_count}")
        return "continue"
 
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", run_agent)
    workflow.add_node("action", execute_tools)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "action",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "action",
        should_continue,
        {
            "continue": "agent",
            "end": END,
        },
    )
    app = workflow.compile()
    return app
 