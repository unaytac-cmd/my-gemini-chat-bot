import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- Streamlit Sayfa Yapılandırması ---
st.set_page_config(
    page_title="Esimde Esim",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("⚡ Esim Ne derse O Olur")
st.write("Merhaba! Ben Ukbe Esim İçin Bu Arayuzu Tasarladim")

# --- API Anahtarı Yapılandırması ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.error("Gemini API Anahtarı bulunamadı.")
        st.stop()

    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Yapılandırma hatası: {e}")
    st.stop()

# --- Gemini Model ve Sohbet Oturumu Başlatma ---
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")

if "chat_session" not in st.session_state:
    # Başlangıçta boş bir geçmişle sohbeti başlatıyoruz
    st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])

# --- Sohbet Geçmişini Gösterme ---
# Gemini'nin kendi tuttuğu history üzerinden mesajları ekrana basıyoruz
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- Kullanıcı Girişi ve Yanıt Üretme ---
if prompt := st.chat_input("Bir şeyler yazın..."):
    # 1. Kullanıcı mesajını anlık göster
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Yanıtı üret ve göster
    with st.chat_message("model"):
        response_placeholder = st.empty() # Akış için yer tutucu
        full_response = ""
        
        try:
            # stream=True ile yanıtı parça parça alıyoruz
            response = st.session_state.chat_session.send_message(prompt, stream=True)
            
            for chunk in response:
                full_response += chunk.text
                # Yazma efektini simüle et
                response_placeholder.markdown(full_response + "▌")
            
            # Yazma bitince imleci kaldır ve son hali bas
            response_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"Hata: {e}")