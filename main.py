# main.py
# VibeCash - AI Expense Extraction Assistant (Kaggle Capstone Project)
# Built using the Google Agent Development Kit (ADK) framework

import asyncio
from datetime import datetime
import os
import sys
import tzlocal
from dotenv import load_dotenv

# Import ADK core primitives
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# =====================================================================
# 1. Environment and Security Setup
# =====================================================================
# Load environment variables from a .env file (if present)
load_dotenv()

# Security Feature: NO hardcoded keys.
# We retrieve the Gemini API key from environment variables.
# The ADK framework internally expects GOOGLE_API_KEY, so we map
# GEMINI_API_KEY to GOOGLE_API_KEY if GOOGLE_API_KEY is not already set.
if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]




# =====================================================================
# 2. Agent Custom Tools (Skills)
# =====================================================================
def get_current_time() -> str:
    """Get the current local date and time.
    
    This tool allows the agent to get the exact current timezone-aware local
    time on the host machine to accurately timestamp expenses.
    
    Returns:
        str: The current local date and time with timezone offset in ISO 8601 format.
    """
    # Fetch local timezone of the host machine
    local_tz = tzlocal.get_localzone()
    # Return timezone-aware ISO string
    return datetime.now(local_tz).isoformat()


def save_expense(item: str, amount: float, currency: str, timestamp: str) -> str:
    """Save an extracted expense to the local expenses.csv file.
    
    Args:
        item: The description or category of the item purchased (e.g., coffee, lunch).
        amount: The monetary value of the expense (numeric).
        currency: The currency symbol or code (e.g. USD, EUR, VND, etc.).
        timestamp: The timezone-aware timestamp when the expense occurred.
        
    Returns:
        str: A confirmation message indicating the expense was logged successfully.
    """
    import csv
    file_exists = os.path.exists("expenses.csv")
    with open("expenses.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Item/Category", "Amount", "Currency"])
        writer.writerow([timestamp, item, amount, currency])
    return f"Successfully logged to CSV: {item} - {amount} {currency} at {timestamp}"


# =====================================================================
# 3. Interactive Chat Loop and Execution
# =====================================================================
async def main():
    # Validate that the API key is configured.
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: API key is not configured.")
        print("Please set the GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")
        print("You can create a '.env' file in this directory with:")
        print("  GOOGLE_API_KEY=your_gemini_api_key_here")
        sys.exit(1)

    # Define constant properties for the session
    APP_NAME = "VibeCash"
    USER_ID = "kaggle_capstone_user"
    SESSION_ID = "vibecash_expense_session"

    # Initialize the in-memory session service to manage chat history
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    # Initialize the ADK Agent with a helpful financial assistant persona.
    # We pass 'get_current_time' and 'save_expense' tools to the tools list.
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

    # Instantiate the Runner to orchestrate agent invocation and tool execution
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    print("=" * 60)
    print("VibeCash Expense Extraction Assistant (ADK Framework)")
    print("Timezone-aware timestamp tool registered successfully.")
    print("Type 'exit' or 'quit' to end the session.")
    print("=" * 60)

    # Continuous terminal loop taking user inputs
    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting VibeCash session. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting VibeCash session. Goodbye!")
            break

        # Wrap the input into the format expected by the GenAI SDK
        content = types.Content(role="user", parts=[types.Part(text=user_input)])
        print("\nVibeCash is processing...", end="", flush=True)

        try:
            # Invoke the agent asynchronously
            events = runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=content
            )

            response_text = ""
            # Gather and print the final response when the run is complete
            async for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text

            # Clear the "processing" indicator and print agent's output
            print("\r" + " " * 30 + "\r", end="", flush=True)
            print(f"VibeCash > {response_text}")

        except Exception as e:
            print(f"\nError: An error occurred during agent processing: {e}")


if __name__ == "__main__":
    asyncio.run(main())
