import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # Suppress INFO and WARNING logs from TensorFlow
os.environ["TRANSFORMERS_BACKEND"] = "pt"
import sys
import threading
import queue
import time
import tempfile
import warnings

# Add the main project directory to Python path without changing working directory
main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if main_dir not in sys.path:
    sys.path.insert(0, main_dir)

import streamlit as st
from agentic_ai.modules.loan_processing.agents.agreement_agent import AgreementAgent

# Ignore deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

st.set_page_config(page_title="Agentic Banking Suite", layout="centered")

st.title("🏦 Agentic Banking Suite")
st.markdown("""
**Your loan journey starts here! How can we assist you today?**
""")

if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "workflow_complete" not in st.session_state:
    st.session_state.workflow_complete = False
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "awaiting_input" not in st.session_state:
    st.session_state.awaiting_input = False
if "input_queue" not in st.session_state:
    st.session_state.input_queue = queue.Queue()
if "output_queue" not in st.session_state:
    st.session_state.output_queue = queue.Queue()
if "agent_thread" not in st.session_state:
    st.session_state.agent_thread = None
if "current_question" not in st.session_state:
    st.session_state.current_question = ""
if "agreement_finalized" not in st.session_state:
    st.session_state.agreement_finalized = False
    
class StreamlitInputProvider:
    def __init__(self, input_queue, output_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
    
    def __call__(self, prompt):
        # Store original prompt for reference
        original_prompt = prompt
        
        # Clean up the prompt and send it to the UI
        # Remove any reasoning or internal markers
        if "AGENT REASONING:" in prompt:
            prompt = prompt.split("AGENT REASONING:", 1)[1].strip()
        if "Action:" in prompt:
            prompt = prompt.split("Action:", 1)[0].strip()
        if "Action Input:" in prompt:
            prompt = prompt.split("Action Input:", 1)[1].strip()
            
        # Make sure to preserve any question marks and important context
        if "?" not in prompt and "?" in original_prompt:
            # Try to extract a better question from the original prompt
            question_parts = original_prompt.split("?")
            if len(question_parts) > 1:
                # Find the part ending with a question mark
                for i, part in enumerate(question_parts[:-1]):
                    potential_q = part.split("\n")[-1].strip() + "?"
                    if len(potential_q) > 5:  # Avoid tiny fragments
                        prompt = potential_q
                        break
        
        # Put both a dict with metadata and the string for backwards compatibility
        self.output_queue.put({
            "type": "question",
            "content": prompt,
            "is_question": True
        })
        self.output_queue.put(prompt)  # For backwards compatibility
        
        # Wait for user response
        try:
            response = self.input_queue.get(timeout=300)  # 5 minute timeout
            return response
        except queue.Empty:
            return "TIMEOUT"

def run_agent_workflow(user_request, input_queue, output_queue):
    """Run the agent workflow in a separate thread"""
    try:
        from agentic_ai.modules.loan_processing.orchestrator.loan_agent_orchestrator import LoanAgentOrchestrator
        
        # Initialize the input provider with the queues
        input_provider = StreamlitInputProvider(input_queue, output_queue)
        orchestrator = LoanAgentOrchestrator(input_provider=input_provider)
        
        # Start the workflow
        st.session_state.awaiting_input = True  # Set to True when we start processing
        result = orchestrator.process_application(user_request)
        
        # Process the result based on its type
        if isinstance(result, str):
            if "LOAN AGREEMENT DIGITALLY ACCEPTED" in result or "LOAN DECLINED" in result:
                # Final acceptance/rejection already sent to output queue by orchestrator
                pass
            else:
                # Regular string result
                output_queue.put(result)
        elif isinstance(result, list):
            for msg in result:
                if isinstance(msg, dict) and "loan_details" in msg:
                    # Special handling for loan details
                    output_queue.put(msg)
                else:
                    # Regular message
                    output_queue.put(msg)
            
            # Only send FINAL_RESULT if needed
            last_msg = result[-1] if result else ""
            if not any("LOAN AGREEMENT DIGITALLY ACCEPTED" in str(msg) or "LOAN DECLINED" in str(msg) for msg in result):
                output_queue.put("FINAL_RESULT: " + str(last_msg))
        
        # Clear awaiting_input flag at the end
        st.session_state.awaiting_input = False
        
    except Exception as e:
        output_queue.put(f"ERROR: {str(e)}")
        st.session_state.awaiting_input = False  # Make sure to clear flag on error

with st.form("initial_request_form"):
    user_request = st.text_input("Enter your loan request (e.g., 'I want a loan of 2 lakhs for medical emergency in Mumbai'):")
    submit_request = st.form_submit_button("Start Application")

if submit_request and user_request:
    # Save any important existing state that should persist
    old_thread = st.session_state.get("agent_thread", None)
    
    # Reset all state variables for new application
    initial_state = {
        "conversation": [f"User: {user_request}"],
        "workflow_complete": False,
        "awaiting_input": True,  # Changed to True initially since we're starting workflow
        "current_question": "",
        "user_request": user_request,
        "agreement_finalized": False,
        "latest_agreement": None,
        "agreement_meta": None,
        "parsed_loan_details": None
    }
    
    # Clear existing thread if running
    if old_thread and old_thread.is_alive():
        # Let old thread finish naturally
        time.sleep(0.5)

    # Create fresh queues for message passing
    input_queue = queue.Queue()
    output_queue = queue.Queue()
    st.session_state.input_queue = input_queue
    st.session_state.output_queue = output_queue
    
    # Update session state with initial values
    for key in initial_state:
        st.session_state[key] = initial_state[key]

    # Start the agent workflow in a separate thread
    st.session_state.agent_thread = threading.Thread(
        target=run_agent_workflow,
        args=(user_request, input_queue, output_queue),
        daemon=True  # Ensure thread doesn't block process exit
    )
    st.session_state.agent_thread.start()
    st.rerun()

if st.session_state.awaiting_input and st.session_state.agent_thread:
    st.write("---")
    st.subheader("Agentic Workflow")
    st.write("**Conversation so far:**")
    
    # Filter out duplicate acceptance prompts - only keep the last one
    filtered_conversation = []
    last_acceptance_prompt = None
    
    for msg in st.session_state.conversation:
        # Check if this is an acceptance prompt
        is_acceptance_prompt = (("I AGREE" in msg and "I ACCEPT" in msg and "to accept the terms" in msg) or
                              ("To proceed with digital acceptance" in msg and "Agent: " in msg))
        
        if is_acceptance_prompt:
            # Store this as the last seen acceptance prompt
            last_acceptance_prompt = msg
        else:
            # Add non-acceptance prompt messages immediately
            filtered_conversation.append(msg)
    
    # Add the last acceptance prompt at the end if it exists
    if last_acceptance_prompt:
        filtered_conversation.append(last_acceptance_prompt)
    
    # Display the filtered conversation
    for msg in filtered_conversation:
        if "LOAN AGREEMENT & TERMS" in msg and "============================" in msg:
            agreement_text = msg[7:] if msg.startswith("Agent: ") else msg
            st.session_state['latest_agreement'] = agreement_text  # Store for later
            st.markdown("**Agent:** ")
            st.markdown("### 📋 Loan Agreement & Terms")
            with st.expander("📄 View Full Agreement Details", expanded=True):
                st.code(agreement_text, language="text")
                st.download_button(
                    label="Download Agreement",
                    data=agreement_text,
                    file_name="loan_agreement.pdf",
                    mime="application/pdf",
                    key=f"download_agreement_{hash(agreement_text[:100])}"
                )

            # --- Tenure selection logic ---
            # Try to get max_tenure and used_tenure from the backend if not already done
            if "agreement_meta" not in st.session_state:
                try:
                    # Try to extract the last loan details from the conversation
                    last_loan_details = None
                    for m in reversed(st.session_state.conversation):
                        if m.startswith("User: "):
                            last_loan_details = m[6:]
                            st.session_state["last_loan_details"] = last_loan_details
                            break
                    if "last_loan_details" in st.session_state:
                        agent = AgreementAgent()
                        meta = agent.present_agreement(st.session_state["last_loan_details"])
                        if isinstance(meta, dict) and "max_tenure" in meta:
                            st.session_state["agreement_meta"] = meta
                            # Store the full parsed loan details dict for accurate regeneration
                            if "loan_details" in meta:
                                st.session_state["parsed_loan_details"] = meta["loan_details"]
                except Exception as e:
                    st.warning(f"Could not fetch tenure options: {e}")

            meta = st.session_state.get("agreement_meta", None)
            parsed_loan_details = st.session_state.get("parsed_loan_details", None)
            last_loan_details = st.session_state.get("last_loan_details", None)
            
            # If we have parsed loan details but no proper meta, get the tenure info
            if parsed_loan_details and (not meta or "max_tenure" not in meta):
                try:
                    agent = AgreementAgent()
                    meta = agent.present_agreement(parsed_loan_details)
                    if isinstance(meta, dict) and "max_tenure" in meta:
                        st.session_state["agreement_meta"] = meta
                except Exception as e:
                    st.warning(f"Could not fetch tenure options from loan details: {e}")
                    meta = st.session_state.get("agreement_meta", None)
            
            # Show tenure selection if we have meta info, regardless of whether we have parsed details
            if meta and meta.get("max_tenure", 0) > 0:
                max_tenure = meta["max_tenure"]
                used_tenure = meta["used_tenure"]
                st.markdown(f"**You can choose your loan tenure (up to {max_tenure} months):**")
                
                # Store the previous tenure selection to detect changes
                previous_tenure = st.session_state.get("previous_tenure", used_tenure)
                
                selected_tenure = st.slider(
                    "Select tenure (months)",
                    min_value=12,
                    max_value=max_tenure,
                    value=used_tenure,
                    step=1,
                    key="tenure_slider"
                )
                
                # If tenure changed, remove acceptance prompts from conversation
                if selected_tenure != previous_tenure:
                    # Remove any existing acceptance prompts
                    st.session_state.conversation = [
                        msg for msg in st.session_state.conversation 
                        if not (("I AGREE" in msg and "I ACCEPT" in msg and "to accept the terms" in msg) or
                              ("To proceed with digital acceptance" in msg and "Agent: " in msg))
                    ]
                    # Update stored tenure
                    st.session_state["previous_tenure"] = selected_tenure
                
                if st.button("Regenerate Agreement with Selected Tenure"):
                    try:
                        agent = AgreementAgent()
                        # Use parsed loan details if available, otherwise fall back to last_loan_details
                        details_for_regen = parsed_loan_details if parsed_loan_details else last_loan_details
                        if not details_for_regen:
                            st.error("No loan details available for regeneration")
                        else:
                            new_meta = agent.regenerate_agreement_with_tenure(details_for_regen, selected_tenure)
                            if isinstance(new_meta, dict) and "agreement_text" in new_meta:
                                # Update the agreement in the conversation
                                agreement_updated = False
                                # First, update or remove the existing agreement
                                for i in range(len(st.session_state.conversation)-1, -1, -1):
                                    if "LOAN AGREEMENT & TERMS" in st.session_state.conversation[i]:
                                        st.session_state.conversation[i] = f"Agent: {new_meta['agreement_text']}"
                                        agreement_updated = True
                                        break
                                
                                # If we couldn't find an agreement to update, add it
                                if not agreement_updated:
                                    st.session_state.conversation.append(f"Agent: {new_meta['agreement_text']}")
                                
                                # Remove any existing acceptance prompts to avoid duplication
                                st.session_state.conversation = [
                                    msg for msg in st.session_state.conversation 
                                    if not ("I AGREE" in msg and "I ACCEPT" in msg and "to accept the terms" in msg)
                                    and not ("To proceed with digital acceptance" in msg)
                                ]
                                
                                st.session_state["agreement_meta"] = new_meta
                                st.session_state["latest_agreement"] = new_meta["agreement_text"]
                                # Update parsed_loan_details for further regenerations
                                if "loan_details" in new_meta:
                                    st.session_state["parsed_loan_details"] = new_meta["loan_details"]
                                st.success(f"Agreement regenerated for {selected_tenure} months.")
                                st.rerun()
                            else:
                                st.error(f"Failed to regenerate agreement: {new_meta}")
                    except Exception as e:
                        st.error(f"Failed to regenerate agreement: {e}")
        elif "LOAN AGREEMENT DIGITALLY ACCEPTED" in msg:
            confirmation_text = msg[7:] if msg.startswith("Agent: ") else msg
            st.markdown("**Agent:** ")
            st.markdown("### ✅ Loan Agreement Accepted")
            with st.expander("📄 View Acceptance Confirmation", expanded=True):
                st.code(confirmation_text, language="text")
        else:
            st.write(msg)
    
    # Check for messages from the agent
    messages_processed = False  # Track if we processed any messages

    # Process all available messages from the queue
    while True:
        try:
            message = st.session_state.output_queue.get_nowait()
            messages_processed = True
            
            # Handle dict messages
            if isinstance(message, dict):
                if "loan_details" in message:
                    # Store loan details for agreement generation
                    st.session_state["parsed_loan_details"] = message["loan_details"]
                    st.session_state["agreement_meta"] = {
                        "loan_details": message["loan_details"],
                        "max_tenure": 60,  # Will be set properly when we call present_agreement
                        "used_tenure": 36   # Will be set properly when we call present_agreement
                    }
                elif message.get("type") == "question":
                    # This is a question from the agent
                    question = message["content"]
                    if not any(msg.endswith(question) for msg in st.session_state.conversation):
                        st.session_state.conversation.append(f"Agent: {question}")
                    st.session_state.current_question = question
                continue

            # Handle string messages
            if not isinstance(message, str):
                continue  # Skip non-string messages
                
            if message.startswith("FINAL_RESULT:"):
                result = message[13:]  # Remove "FINAL_RESULT:" prefix
                st.session_state.conversation.append(f"Agent: {result}")
                st.session_state.workflow_complete = True
                st.session_state.awaiting_input = False
                st.session_state.current_question = ""  # Clear any lingering question
                st.success("Loan application workflow completed!")
                break
            elif message.startswith("ERROR:"):
                error = message[6:]  # Remove "ERROR:" prefix
                st.error(f"Workflow error: {error}")
                st.session_state.workflow_complete = True
                st.session_state.awaiting_input = False
                st.session_state.current_question = ""  # Clear any lingering question
                break
            # If the message is a list (e.g., [agreement, prompt]), append each item in order
            elif isinstance(message, list):
                for m in message:
                    # Check if this item is a dict with loan_details
                    if isinstance(m, dict) and "loan_details" in m:
                        st.session_state["parsed_loan_details"] = m["loan_details"]
                        st.session_state["agreement_meta"] = {
                            "loan_details": m["loan_details"],
                            "max_tenure": 60,  
                            "used_tenure": 36   
                        }
                    else:
                        st.session_state.conversation.append(f"Agent: {m}")
                        # Set as current question if it appears to be a question
                        if ("?" in m or m.strip().lower().startswith("please") or m.strip().lower().startswith("provide")):
                            st.session_state.current_question = m
            else:
                # Check if this message contains a loan agreement
                if "LOAN AGREEMENT & TERMS" in message and "============================" in message:
                    # This is the full agreement
                    if not any("LOAN AGREEMENT & TERMS" in msg for msg in st.session_state.conversation):
                        st.session_state.conversation.append(f"Agent: {message}")
                    st.session_state['latest_agreement'] = message
                    # Do not set as current question
                # Check if this is an acceptance prompt
                elif (("I AGREE" in message and "I ACCEPT" in message) or 
                      ("To proceed with digital acceptance" in message)):
                    
                    # Only process if not already finalized
                    if (not "LOAN AGREEMENT DIGITALLY ACCEPTED" in message and 
                        not "LOAN DECLINED" in message and 
                        not st.session_state.agreement_finalized):
                        
                        # Remove any previous acceptance prompts
                        st.session_state.conversation = [
                            msg for msg in st.session_state.conversation 
                            if not (("I AGREE" in msg and "I ACCEPT" in msg and "to accept the terms" in msg) or
                                  ("To proceed with digital acceptance" in msg and "Agent: " in msg))
                        ]
                        
                        # Add the new prompt if we have an agreement
                        if 'latest_agreement' in st.session_state and st.session_state['latest_agreement']:
                            st.session_state.conversation.append(f"Agent: {message}")
                            st.session_state.current_question = message
                elif "LOAN AGREEMENT DIGITALLY ACCEPTED" in message or "LOAN DECLINED" in message:
                    # Final confirmation
                    if not any(msg.endswith(message) for msg in st.session_state.conversation):
                        st.session_state.conversation.append(f"Agent: {message}")
                    st.session_state.workflow_complete = True
                    st.session_state.awaiting_input = False
                    st.session_state.agreement_finalized = True
                    st.session_state.current_question = ""
                    st.success("Loan application workflow completed!")
                    break
                else:
                    # Regular agent question or response
                    # Add to conversation if not already there
                    if not any(msg.endswith(message) for msg in st.session_state.conversation):
                        st.session_state.conversation.append(f"Agent: {message}")
                        # Set as current question if it appears to be a question
                        if ("?" in message or 
                            message.strip().lower().startswith("please") or 
                            message.strip().lower().startswith("provide") or
                            len(st.session_state.conversation) <= 2):  # Also treat first agent message as a question
                            st.session_state.current_question = message

        except queue.Empty:
            # No more messages to process
            break
        except Exception as e:
            st.error(f"Error processing message: {e}")
            # Continue to next message instead of breaking
    
    # If workflow is complete, stop here and don't show any more input fields
    if not st.session_state.workflow_complete:
        # Show current question and get user input (only if workflow is not complete)
        if st.session_state.current_question and not st.session_state.workflow_complete:
            # Always display the agent's question
            st.write(f"**{st.session_state.current_question}**")
            
            # Choose the appropriate input method based on the question type
            current_q = st.session_state.current_question.lower()
            
            # Detect if the agent is asking for a salary PDF path
            if ("salary pdf" in current_q or
                "salary slip" in current_q or
                "pdf document" in current_q or
                "provide the path" in current_q):
                # Only show the file uploader, no text input field
                uploaded_file = st.file_uploader("Upload your salary PDF", type=["pdf"])
                if uploaded_file is not None:
                    # Save uploaded file inside project directory
                    upload_dir = os.path.join(main_dir, "uploaded_files")
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.read())
                    st.session_state.conversation.append(f"User uploaded: {uploaded_file.name}")
                    st.session_state.input_queue.put(file_path)
                    st.session_state.current_question = ""
                    st.rerun()
            
            # Special cases for consent questions
            elif "consent" in current_q or "permission" in current_q or "authorize" in current_q or "authorise" in current_q:
                # This is likely a consent question - show consent-specific buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button('I Give My Consent'):
                        st.session_state.conversation.append('User: I give my consent')
                        st.session_state.input_queue.put('yes')
                        st.session_state.current_question = ''
                        st.rerun()
                with col2:
                    if st.button('I Do Not Consent'):
                        st.session_state.conversation.append('User: I do not give my consent')
                        st.session_state.input_queue.put('no')
                        st.session_state.current_question = ''
                        st.rerun()
            
            # Detect if the agent is asking for a yes/no or accept/reject question
            elif ("yes" in current_q and "no" in current_q) or (("accept" in current_q or "agree" in current_q) and ("reject" in current_q or "decline" in current_q)):
                # Show appropriate yes/no or accept/reject buttons
                accept_reject = (("accept" in current_q or "agree" in current_q) and ("reject" in current_q or "decline" in current_q))
                if accept_reject:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button('I ACCEPT'):
                            st.session_state.conversation.append('User: I ACCEPT')
                            st.session_state.input_queue.put('I ACCEPT')
                            st.session_state.current_question = ''
                            st.rerun()
                    with col2:
                        if st.button('I REJECT'):
                            st.session_state.conversation.append('User: I REJECT')
                            st.session_state.input_queue.put('I REJECT')
                            st.session_state.current_question = ''
                            st.rerun()
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button('Yes'):
                            st.session_state.conversation.append('User: yes')
                            st.session_state.input_queue.put('yes')
                            st.session_state.current_question = ''
                            st.rerun()
                    with col2:
                        if st.button('No'):
                            st.session_state.conversation.append('User: no')
                            st.session_state.input_queue.put('no')
                            st.session_state.current_question = ''
                            st.rerun()
            
            # Default case: regular text input
            else:
                user_reply = st.text_input("Your response:", key=f"response_{len(st.session_state.conversation)}")
                if st.button("Submit"):
                    if user_reply.strip():
                        st.session_state.conversation.append(f"User: {user_reply}")
                        st.session_state.input_queue.put(user_reply)
                        st.session_state.current_question = "" # Clear the current question immediately
                        st.rerun() # Rerun to wait for the next agent response
                    else:
                        st.warning("Please enter a response before submitting.")
        else:
            st.info("⏳ Waiting for agent response...")
            time.sleep(1) # Add a small delay to prevent rapid-fire reruns
            st.rerun()