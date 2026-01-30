import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Printnest AI",
    page_icon="💼",
    layout="wide"
)

# --- 2. API ANAHTARI VE YAPILANDIRMA ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.error("API Key not found!")
        st.stop()

    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Config Error: {e}")
    st.stop()

# --- 3. MODEL VE CANLI ARAMA AYARI (HATASIZ YAPI) ---
if "gemini_model" not in st.session_state:
    try:
        # En yeni SDK sürümünde en güvenli araç tanımlama yöntemi budur.
        # Manuel sözlük yerine doğrudan araç ismini liste içinde gönderiyoruz.
        # Bu yöntem 'Unknown field for FunctionDeclaration' hatasını engeller.
        st.session_state.gemini_model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            tools=['google_search'] 
        )
    except Exception as e:
        st.error(f"Model Initialization Error: {e}")
        st.stop()

if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])

# --- 4. YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.title("💼 Printnest AI")
    if st.button("➕ New Task", use_container_width=True):
        st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])
        st.rerun()
    st.divider()
    st.caption("Workspace Status: Online")

# --- 5. ANA EKRAN ---
st.title("🚀 Printnest Corporate AI")

# --- 6. SOHBET GEÇMİŞİ ---
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 7. MESAJ GİRİŞİ VE YANIT ---
if prompt := st.chat_input("How can I help you today?"):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            response = st.session_state.chat_message.send_message(prompt, stream=True)
            
            for chunk in response:
                if hasattr(chunk, 'text'):
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"Chat Error: {e}")