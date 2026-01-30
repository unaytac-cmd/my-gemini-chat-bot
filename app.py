import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- 1. SAYFA YAPILANDIRMASI (OFFICE EDITION) ---
st.set_page_config(
    page_title="Printnest AI",
    page_icon="💼",
    layout="wide", # Ofis kullanımı için geniş ekran
    initial_sidebar_state="expanded"
)

# --- 2. API ANAHTARI VE YAPILANDIRMA ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.error("Gemini API Key not found. Please check your secrets.")
        st.stop()

    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# --- 3. MODEL VE CANLI ARAMA AYARI ---
if "gemini_model" not in st.session_state:
    try:
        # Belirttiğin gemini-2.5-flash modeli ve canlı Google araması
        st.session_state.gemini_model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            tools=[{"google_search_retrieval": {}}]
        )
    except Exception as e:
        st.error(f"Model Initialization Error: {e}")
        st.stop()

if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])

# --- 4. YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.title("💼 Printnest AI")
    st.subheader("Corporate Workspace")
    
    if st.button("➕ New Task", use_container_width=True):
        st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])
        st.rerun()
    
    st.divider()
    st.caption("Recent Activities")
    st.info("History logging will be enabled after DB integration.")
    
    st.divider()
    if st.button("Sign Out", use_container_width=True):
        st.write("Auth redirect...")

# --- 5. ANA EKRAN ---
st.title("🚀 Printnest Corporate AI")
st.write("Welcome to your intelligent workspace. I can help with market analysis, printing projects, or daily office tasks.")

# --- 6. SOHBET GEÇMİŞİNİ GÖSTERME ---
# Gemini'nin kendi history'sini kullanarak çift yazmayı engelliyoruz
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 7. MESAJ GİRİŞİ VE YANIT SÜRECİ ---
if prompt := st.chat_input("Enter your task or question here..."):
    # Kullanıcı mesajını göster
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gemini'den yanıt al ve göster
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # stream=True ile akışkan cevap
            response = st.session_state.chat_session.send_message(prompt, stream=True)
            
            for chunk in response:
                if hasattr(chunk, 'text'):
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")