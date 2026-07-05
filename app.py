# app.py
# VibeCash - AI Expense Extraction Assistant (Streamlit Web Front-End)
# Phase 2: Web Front-End (Glossarium Aesthetic)

import asyncio
import os
import streamlit as st
from dotenv import load_dotenv
import tzlocal
from datetime import datetime

# Import ADK core primitives and the custom tools from main.py
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from main import get_current_time, save_expense

# =====================================================================
# 1. Environment & API Key Setup
# =====================================================================
load_dotenv()

# Security Feature: NO hardcoded keys. Map GEMINI_API_KEY if needed.
if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

# =====================================================================
# 2. Streamlit Page Configuration (Glossarium Aesthetic)
# =====================================================================
st.set_page_config(
    page_title="VibeCash - Expense Extractor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Blue & White Glossarium Aesthetic
st.markdown("""
<style>
    /* Main Layout Styling */
    .stApp {
        background-color: #ffffff;
        color: #1e293b;
    }
    
    /* Input Box Customization */
    .stChatInputContainer {
        border-radius: 8px;
        border: 1px solid #cbd5e1;
    }
    
    /* Custom Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Styled Markdown Cards */
    .info-card {
        background-color: #f1f5f9;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1d4ed8;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 3. Sidebar Setup (Project Info)
# =====================================================================
with st.sidebar:
    st.title("Project Info")
    st.markdown("""
    <div class="info-card">
        <strong>VibeCash</strong> is an automated expense extraction assistant built for the Kaggle Capstone Project.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### How it Works:
    1. Enter your daily expenses in natural language.
    2. The agent calls the timezone-aware local time skill.
    3. The agent parses details and returns a structured output.
    
    ### Tech Stack:
    - **UI**: Streamlit
    - **Framework**: Google ADK
    - **Model**: `gemini-3.5-flash`
    """)
    
    st.divider()
    
    # API Configuration status indicator
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        api_key_input = st.text_input("Enter Gemini API Key", type="password", help="Enter your Gemini API key here to enable VibeCash.")
        if api_key_input:
            os.environ["GOOGLE_API_KEY"] = api_key_input
            api_key = api_key_input
            st.rerun()

    if api_key:
        st.success("🔒 API Key: Configured")
    else:
        st.error("🔓 API Key: Not Found")
        st.warning("Please add GOOGLE_API_KEY to your environment variables or enter it above to run VibeCash.")

# =====================================================================
# 4. Glossarium-style Header (Blue background, White text)
# =====================================================================
st.markdown("""
<div style="background-color: #1d4ed8; padding: 25px; border-radius: 10px; margin-bottom: 25px; text-align: center;">
    <h1 style="color: #ffffff; margin: 0; font-family: 'Outfit', 'Inter', sans-serif; font-size: 2.2em; font-weight: 700;">
        VibeCash Expense Assistant
    </h1>
    <p style="color: #bfdbfe; margin: 8px 0 0 0; font-family: 'Inter', sans-serif; font-size: 1.1em;">
        Extract and timestamp your daily expenses automatically using Gemini and ADK
    </p>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# 5. ADK Agent & Runner Initialization (Cached in st.session_state)
# =====================================================================
APP_NAME = "VibeCashWeb"
USER_ID = "web_user"
SESSION_ID = "web_session"

if "runner" not in st.session_state and api_key:
    session_service = InMemorySessionService()
    
    # Create the session asynchronously
    async def init_session():
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
    asyncio.run(init_session())
    
    agent = Agent(
        model="gemini-3.5-flash",
        name="VibeCash",
        instruction=(
            "You are VibeCash, a helpful financial expense extraction assistant. "
            "Your goal is to parse user descriptions of daily expenses (e.g., 'I bought coffee for 20000') "
            "and extract the expense details (item/category, amount, currency, timestamp). "
            "To timestamp the expenses accurately, you MUST use the 'get_current_time' tool "
            "to retrieve the current local date and time. "
            "Once you have extracted the details, you MUST invoke the 'save_expense' tool to "
            "persist the expense to the local 'expenses.csv' file. Finally, output the extracted "
            "expense details clearly in a structured format (like markdown table or JSON) to the "
            "user and confirm that the transaction has been recorded."
        ),
        tools=[get_current_time, save_expense],
    )
    
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    st.session_state.runner = runner

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# =====================================================================
# 6. Main Chat Area
# =====================================================================
# Display prior messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Async helper to query the ADK agent
async def get_agent_response(user_message: str):
    content = types.Content(role="user", parts=[types.Part(text=user_message)])
    events = st.session_state.runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    )
    response_text = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text
    return response_text

# Disabled state for input box
chat_disabled = not api_key

# Warn user if chat is disabled
if chat_disabled:
    st.info("💡 Tip: Enter a Gemini API Key in the sidebar/Project Info to enable the chat input.")

# Accept chat input
if prompt := st.chat_input(
    "Enter your expense (e.g., 'I bought lunch for 15000')",
    disabled=chat_disabled
):
    # Display user input
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Process agent response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("VibeCash is extracting expense details...")
        
        try:
            # Execute async query in sync Streamlit context
            response = asyncio.run(get_agent_response(prompt))
            message_placeholder.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            error_msg = f"An error occurred while calling the agent: {e}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
