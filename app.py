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

# --- 3. MODEL VE CANLI ARAMA AYARI (YENİ STANDART) ---
if "gemini_model" not in st.session_state:
    try:
        # Hata mesajındaki talimata göre sadece 'google_search' ismini kullanıyoruz.
        # En yeni SDK'larda bu yapı bir 'Tool' objesi olarak tanımlanır.
        st.session_state.gemini_model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash",
            tools=[{"google_search": {}}] # Sözlük yapısı ama isim 'google_search'
        )
    except Exception as e:
        # Eğer yukarıdaki hata verirse, fallback olarak en sade listeyi dener:
        try:
            st.session_state.gemini_model = genai.GenerativeModel(
                model_name="models/gemini-2.5-flash",
                tools=['google_search']
            )
        except:
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
    st.caption("Office Workspace")

# --- 5. ANA EKRAN ---
st.title("🚀 Printnest Corporate AI")

# --- 6. SOHBET GEÇMİŞİ ---
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 7. MESAJ GİRİŞİ VE YANIT ---
if prompt := st.chat_input("Ask me anything about today's market..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Yanıt alırken model artık otomatik olarak Google Search kullanacak
            response = st.session_state.chat_session.send_message(prompt, stream=True)
            
            for chunk in response:
                if hasattr(chunk, 'text'):
                    full_response += chunk.text
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"Chat Error: {e}")