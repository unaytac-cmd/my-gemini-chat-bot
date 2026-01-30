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
        st.error("API Key not found! Please check your configuration.")
        st.stop()

    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Config Error: {e}")
    st.stop()

# --- 3. MODEL TANIMLAMA (STABİL VERSİYON) ---
# Google Search araçlarını hata verdiği için şimdilik kaldırıyoruz.
# Saf model çok daha hızlı ve hatasız çalışacaktır.
if "gemini_model" not in st.session_state:
    try:
        st.session_state.gemini_model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash"
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
    
    if st.button("➕ New Task / Clear Chat", use_container_width=True):
        st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])
        st.rerun()
    
    st.divider()
    st.caption("Workspace Status: Stable 🟢")
    st.info("System optimized for speed and reliability.")

# --- 5. ANA EKRAN ---
st.title("🚀 Printnest Corporate AI")
st.write("Professional assistant for office tasks, creative projects, and analysis.")

# --- 6. SOHBET GEÇMİŞİNİ GÖSTERME ---
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 7. MESAJ GİRİŞİ VE YANIT SÜRECİ ---
if prompt := st.chat_input("How can I assist you today?"):
    # Kullanıcı mesajını göster
    with st.chat_message("user"):
        st.markdown(prompt)

    # Yanıtı üret
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Stream ile hızlı yanıt
            response = st.session_state.chat_session.send_message(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"Chat Error: {e}")