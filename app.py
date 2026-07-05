# app.py
# VibeCash - AI Expense Extraction Assistant (Streamlit Web Front-End)
# Phase 2: Web Front-End (Glossarium Aesthetic)

import asyncio
import os
import re
import json
import pandas as pd
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


def extract_and_format_json(text: str):
    """Searches for a JSON block in the response text and converts it to a DataFrame."""
    # Look for json code blocks or raw json structure
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not json_match:
        json_match = re.search(r"(\{.*?\})", text, re.DOTALL)
        
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            # Format to columns 'Field' and 'Value'
            df_data = []
            
            # Fetch and normalize currency code (standard 3-letter ISO code, e.g. "USD", "IDR")
            currency = str(data.get("Currency", "USD")).strip().upper()
            if len(currency) != 3:
                if currency == "$":
                    currency = "USD"
                elif currency in ["RP", "IDR"]:
                    currency = "IDR"
                else:
                    currency = "USD"
            
            # Implement currency symbol mapping specifically for Amount row
            currency_symbols = {
                "USD": "$",
                "IDR": "Rp",
                "EUR": "€",
                "VND": "₫",
                "GBP": "£",
                "JPY": "¥",
                "SGD": "S$"
            }
            symbol = currency_symbols.get(currency, currency)
            space = " " if len(symbol) > 1 else ""
            
            for k, v in data.items():
                val = str(v)
                if k == "Amount":
                    try:
                        amt_val = float(v)
                        if amt_val.is_integer():
                            val = f"{symbol}{space}{int(amt_val):,}"
                        else:
                            val = f"{symbol}{space}{amt_val:,.2f}"
                    except ValueError:
                        val = f"{symbol}{space}{v}"
                elif k == "Currency":
                    val = currency
                df_data.append({"Field": k, "Value": val})
            
            df = pd.DataFrame(df_data)
            # Remove the JSON substring from text output
            clean_text = text.replace(json_match.group(0), "").strip()
            return df, clean_text
        except Exception:
            pass
    return None, text




# =====================================================================
# 1. Environment & API Key Setup
# =====================================================================
load_dotenv()

# Security Feature: NO hardcoded keys. Map GEMINI_API_KEY if needed.
if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def get_realtime_metrics():
    """Reads expenses.csv to calculate real-time stats."""
    import csv
    total_expenses_today = 0.0
    total_transactions = 0
    currency_code = "USD"
    
    if os.path.exists("expenses.csv"):
        try:
            local_tz = tzlocal.get_localzone()
            today_str = datetime.now(local_tz).strftime("%Y-%m-%d")
            
            with open("expenses.csv", "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)  # skip header
                if header:
                    for row in reader:
                        if not row or len(row) < 4:
                            continue
                        timestamp, item, amount_str, currency = row[:4]
                        total_transactions += 1
                        # Check if transaction timestamp is today
                        if timestamp.startswith(today_str):
                            try:
                                total_expenses_today += float(amount_str)
                                if currency:
                                    currency_code = currency.strip().upper()
                            except ValueError:
                                pass
        except Exception:
            pass
            
    return total_expenses_today, total_transactions, currency_code



# =====================================================================
# 2. Streamlit Page Configuration (Glossarium Aesthetic)
# =====================================================================
st.set_page_config(
    page_title="VibeCash - Expense Extractor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Pastel Gradient Theme with Glassmorphism and Drop-Shadow Cards
st.markdown("""
<style>
    /* Main Layout Styling - Pastel Gradient */
    .stApp {
        background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
        color: #1e293b;
    }
    
    /* Input Box Customization and Readability */
    .stChatInputContainer {
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        background-color: #ffffff !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .stChatInput textarea {
        color: #1e293b !important;
    }
    
    /* Custom Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(248, 250, 252, 0.85);
        border-right: 1px solid #e2e8f0;
    }
    
    /* Glossarium white background card for metrics with drop shadow */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid rgba(226, 232, 240, 0.8);
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 3. Sidebar Setup (Project Info)
# =====================================================================
with st.sidebar:
    st.title("Project Info")
    st.info("**VibeCash** is an automated expense extraction assistant built for the Kaggle Capstone Project. Leveraging the Google Agent Development Kit (ADK) and Gemini 3.5 Flash, it automatically parses daily transactions.")
    
    with st.expander("🔍 How it Works", expanded=True):
        st.markdown("""
        1. **Enter Expense**: Log transactions using natural conversational language.
        2. **Retrieve Time**: The agent dynamically fetches the timezone-aware local time from the host machine.
        3. **Process & Store**: Details (item, amount, currency, timestamp) are extracted and saved directly to the local CSV.
        4. **Structured Summary**: Provides a clear, formatted confirmation display.
        """)
        
    with st.expander("🛠️ Tech Stack"):
        st.markdown("""
        - **UI/UX**: Streamlit (Glossarium style)
        - **Framework**: Google ADK
        - **Brain Model**: `gemini-3.5-flash`
        - **Time System**: `tzlocal` & `datetime`
        - **Data Store**: Flat-file CSV
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
<div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); padding: 30px; border-radius: 16px; margin-bottom: 25px; text-align: center; box-shadow: 0 10px 20px -5px rgba(37, 99, 235, 0.3);">
    <h1 style="color: #ffffff; margin: 0; font-family: 'Outfit', 'Inter', sans-serif; font-size: 2.2em; font-weight: 700;">
        VibeCash Expense Assistant
    </h1>
    <p style="color: #bfdbfe; margin: 8px 0 0 0; font-family: 'Inter', sans-serif; font-size: 1.1em;">
        Extract and timestamp your daily expenses automatically with VibeCash
    </p>
</div>
""", unsafe_allow_html=True)

# Fetch real-time metrics from CSV
total_today, total_tx, currency_code = get_realtime_metrics()

if total_today == 0:
    today_val = f"{currency_code} 0"
elif total_today.is_integer():
    today_val = f"{currency_code} {int(total_today):,}"
else:
    today_val = f"{currency_code} {total_today:,.2f}"

total_tx_val = str(total_tx)

# Metric Dashboard just below main header
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Today's Expenses", value=today_val)
with col2:
    st.metric(label="Total Transactions", value=total_tx_val)
with col3:
    st.metric(label="System Status", value="Online")

st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)






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
            "Your goal is to parse user descriptions of daily expenses (e.g., 'I bought 2 coffees for 40000') "
            "and extract the expense details including the quantity and item category. "
            "To timestamp the expenses accurately, you MUST use the 'get_current_time' tool "
            "to retrieve the current local date and time. "
            "Once you have extracted the details, you MUST invoke the 'save_expense' tool to "
            "persist the expense to the local 'expenses.csv' file. Finally, you MUST output the "
            "extracted details as a JSON code block in your response. The JSON block should strictly "
            "have the following keys: 'Item', 'Amount', 'Currency', 'Timestamp', 'Quantity', and 'Category'. "
            "For example:\n"
            "```json\n"
            "{\n"
            "  \"Item\": \"coffee\",\n"
            "  \"Amount\": 40000,\n"
            "  \"Currency\": \"VND\",\n"
            "  \"Timestamp\": \"2026-07-06T02:05:29+07:00\",\n"
            "  \"Quantity\": 2,\n"
            "  \"Category\": \"Food & Beverage\"\n"
            "}\n"
            "```\n"
            "Confirm to the user that the transaction has been recorded successfully."
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
        if msg.get("df") is not None:
            if msg.get("content"):
                st.markdown(msg["content"])
            st.dataframe(msg["df"], use_container_width=True, hide_index=True)
        elif msg.get("is_warning"):
            st.warning(msg["content"])
        else:
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
            df, clean_text = extract_and_format_json(response)
            
            if df is not None:
                if clean_text.strip():
                    message_placeholder.markdown(clean_text)
                else:
                    message_placeholder.empty()
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": clean_text,
                    "df": df
                })
            else:
                message_placeholder.markdown(response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "rate limit" in error_str.lower():
                warning_msg = "Whoops! VibeCash is taking a quick breather to process everything. Please wait a few seconds before your next input. 🧘‍♀️"
                message_placeholder.warning(warning_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": warning_msg,
                    "is_warning": True
                })
            else:
                error_msg = f"An error occurred while calling the agent: {e}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
