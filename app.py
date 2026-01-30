import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Printnest AI",
    page_icon="💼",
    layout="wide"
)

# --- 2. API CONFIGURATION ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.error("API Key not found! Please add GOOGLE_API_KEY to your secrets.")
        st.stop()

    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# --- 3. MODEL & LIVE SEARCH SETUP ---
if "gemini_model" not in st.session_state:
    try:
        # tools=['google_search'] is the most stable format for 2.5-flash
        st.session_state.gemini_model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            tools=['google_search']
        )
    except Exception as e:
        st.error(f"Model Initialization Error: {e}")
        st.stop()

if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])

# --- 4. SIDEBAR (WORKSPACE) ---
with st.sidebar:
    st.title("💼 Printnest AI")
    st.subheader("Corporate Workspace")
    
    if st.button("➕ New Task", use_container_width=True):
        st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])
        st.rerun()
    
    st.divider()
    st.caption("Workspace Activities")
    st.info("History logging will be enabled in the next update (DB Integration).")

# --- 5. MAIN INTERFACE ---
st.title("🚀 Printnest Corporate AI")
st.write("Welcome to your intelligent workspace. Use me for market data, analysis, or office projects.")

# --- 6. DISPLAY CHAT HISTORY ---
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 7. CHAT INPUT & RESPONSE LOGIC ---
if prompt := st.chat_input("Ask about stock prices, news, or office tasks..."):
    # Show User Message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and Stream Assistant Response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # We use stream=True for professional real-time feel
            response = st.session_state.chat_session.send_message(prompt, stream=True)
            
            for chunk in response:
                # Basic check to ensure chunk has text
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"Chat Error: {e}")