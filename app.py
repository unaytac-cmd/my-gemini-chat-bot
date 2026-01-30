import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")

# --- 2. API CONFIG ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Config Error: {e}")
    st.stop()

# --- 3. MODEL SETUP (GÜNCEL GEMINI 2.5) ---
if "gemini_model" not in st.session_state:
    try:
        # En güncel SDK yapısı: google_search
        st.session_state.gemini_model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            tools=[{"google_search": {}}]
        )
    except:
        st.session_state.gemini_model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            tools=['google_search']
        )

if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("💼 Printnest AI")
    if st.button("➕ New Task", use_container_width=True):
        st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])
        st.rerun()

# --- 5. MAIN UI ---
st.title("🚀 Printnest Corporate AI")

# Display Messages
for message in st.session_state.chat_session.history:
    with st.chat_message("assistant" if message.role == "model" else "user"):
        st.markdown(message.parts[0].text)

# Chat Input
if prompt := st.chat_input("Ask about 2026 market data..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        try:
            response = st.session_state.chat_session.send_message(prompt, stream=True)
            for chunk in response:
                if hasattr(chunk, 'text'):
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)
        except Exception as e:
            st.error(f"Chat Error: {e}")