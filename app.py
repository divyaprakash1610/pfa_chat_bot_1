import streamlit as st
from modules.chat_manager import ChatManager
from modules.phq_gad import OPTIONS
import json

# ---------------------------
# Session state for PHQ/GAD
# ---------------------------
if "test_phase" not in st.session_state:
    st.session_state.test_phase = False
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "phq_scores" not in st.session_state:
    st.session_state.phq_scores = []
if "gad_scores" not in st.session_state:
    st.session_state.gad_scores = []
if "show_test_prompt_buttons" not in st.session_state:
    st.session_state.show_test_prompt_buttons = False
if "pending_test_type" not in st.session_state:
    st.session_state.pending_test_type = "PHQ9"

# ---------------------------
# Page setup
# ---------------------------
st.set_page_config(page_title="🧠 Student Mental Health Bot")
st.title("🧠 Student Mental Health Support Bot")

# ---------------------------
# Initialize chat manager
# ---------------------------
if "chat" not in st.session_state:
    st.session_state.chat = ChatManager()
chat = st.session_state.chat

# ---------------------------
# API Mode (for frontend fetch)
# ---------------------------
params = st.query_params
api_mode = params.get("api", ["0"])[0] == "1"

if api_mode:
    # Only return overall risk score as JSON
    result = {}
    if chat.phq9_completed and chat.gad7_completed:
        result["overall_risk"] = chat.calculate_overall_risk()
    else:
        result["overall_risk"] = None

    st.write(result)
    st.stop()

# ---------------------------
# Display chat history
# ---------------------------
for msg in chat.get_messages():
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------
# Handle test prompt buttons (Yes/No)
# ---------------------------
if st.session_state.show_test_prompt_buttons and not st.session_state.test_phase:
    test_type = st.session_state.pending_test_type

    if test_type == "PHQ9":
        st.markdown("*Would you like to take the PHQ-9 and GAD-7 questionnaires?*")
    else:
        st.markdown("*Would you like to complete the GAD-7 questionnaire now?*")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Yes, start now", key=f"start_test_{test_type}", use_container_width=True):
            chat.start_test(test_type)  # Reset prompted_for_test flag
            st.session_state.show_test_prompt_buttons = False
            st.session_state.test_phase = True
            st.session_state.current_question = chat.start_test(test_type)
            if st.session_state.current_question:
                test_name = "PHQ-9" if test_type == "PHQ9" else "GAD-7"
                question_msg = f"{test_name} Question {chat.test_index + 1}/{len(chat.current_test)}: {st.session_state.current_question}"
                chat.add_bot_message(question_msg)
                with st.chat_message("assistant"):
                    st.markdown(question_msg)
            st.rerun()

    with col2:
        if st.button("❌ No, maybe later", key=f"decline_test_{test_type}", use_container_width=True):
            chat.decline_test(test_type)
            if test_type == "PHQ9":
                reply = "🧠 No problem! We can continue chatting. I'll check in with you again later about the questionnaires."
            else:  # GAD7
                reply = "🧠 That's okay! We can continue our conversation. The GAD-7 can wait for another time."
            chat.add_bot_message(reply)
            st.session_state.show_test_prompt_buttons = False
            with st.chat_message("assistant"):
                st.markdown(reply)
            st.rerun()

# ---------------------------
# Handle questionnaire options (4 option buttons)
# ---------------------------
if (
    chat.current_test is not None
    and st.session_state.test_phase
    and st.session_state.current_question
    and chat.test_index < len(chat.current_test)
):
    st.markdown("---")
    st.markdown(f"*Question {chat.test_index + 1}/{len(chat.current_test)}*: {st.session_state.current_question}")
    st.markdown("*Please select one option:*")

    # Create 4 buttons for the response options
    for idx, (label, score) in enumerate(OPTIONS):
        if st.button(
            f"{idx}: {label}",
            key=f"option_{chat.test_index}{score}{idx}",
            use_container_width=True,
        ):
            result = chat.record_answer(score)

            if result is None:
                # Error occurred
                st.session_state.test_phase = False
                st.session_state.current_question = None
                error_msg = "🧠 It looks like there was an issue. Let's continue chatting, or you can start the questionnaire again later."
                chat.add_bot_message(error_msg)
                with st.chat_message("assistant"):
                    st.markdown(error_msg)

            elif isinstance(result, tuple):
                # Test completed, result is (risk_level, test_name)
                risk_level, completed_test = result
                st.session_state.test_phase = False
                st.session_state.current_question = None

                # Show results
                if completed_test == "PHQ9":
                    result_message = f"✅ *PHQ-9 Complete!* Your depression screening result: *{risk_level.upper()}*"
                    chat.add_bot_message(result_message)
                    with st.chat_message("assistant"):
                        st.markdown(result_message)
                else:
                    overall_risk = chat.calculate_overall_risk()
                    result_message = f"✅ *GAD-7 Complete!* Your anxiety screening result: *{risk_level.upper()}*\n\n"
                    result_message += f"📊 Overall Assessment Summary:\n"
                    result_message += f"• Depression (PHQ-9): *{chat.phq9_risk.upper()}*\n"
                    result_message += f"• Anxiety (GAD-7): *{chat.gad7_risk.upper()}*\n"
                    result_message += f"• *Overall Risk Level: {overall_risk.upper()}*\n"
                    chat.add_bot_message(result_message)
                    with st.chat_message("assistant"):
                        st.markdown(result_message)

            else:
                # Next question
                st.session_state.current_question = result
                if chat.current_test is not None:
                    next_question_msg = f"*Question {chat.test_index + 1}/{len(chat.current_test)}*: {result}"
                    chat.add_bot_message(next_question_msg)

            st.rerun()

# ---------------------------
# User input
# ---------------------------
if user_input := st.chat_input("Type your message here...", disabled=st.session_state.test_phase):
    chat.add_user_message(user_input)
    with st.chat_message("user"):
        st.markdown(user_input)

    if not st.session_state.test_phase:
        bot_reply, show_buttons, test_type = chat.generate_reply(user_input)
        st.session_state.show_test_prompt_buttons = show_buttons
        st.session_state.pending_test_type = test_type

        with st.chat_message("assistant"):
            st.markdown(bot_reply)

        if show_buttons:
            st.rerun()