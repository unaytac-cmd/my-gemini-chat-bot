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

# --- API Anahtarını Yükleme ve GenAI Kütüphanesini Yapılandırma ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            st.error("Gemini API Anahtarı bulunamadı. Lütfen gerekli adımları tamamlayın.")
            st.stop()

    genai.configure(api_key=api_key)

except Exception as e:
    st.error(f"API anahtarı yapılandırma hatası oluştu: {e}")
    st.stop()

# --- Gemini GenerativeModel'i Ayarlama ve Sohbet Oturumunu Başlatma ---
# Bu blok, model ve sohbet oturumunu sadece bir kez başlatmak için önemlidir.
# Streamlit'in yeniden çalıştırma davranışını yönetmek için `st.session_state` kullanılır.
if "gemini_model" not in st.session_state:
    try:
        st.session_state.gemini_model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash" # Model adının doğru olduğundan emin olun
            # generation_config ve safety_settings burada da eklenebilir
        )
    except Exception as e:
        st.error(f"Gemini modeli başlatılırken bir hata oluştu: {e}")
        st.markdown("Lütfen API anahtarınızın geçerli olduğundan ve 'models/gemini-2.5-flash' modeline erişim izninizin olduğundan emin olun.")
        st.stop()

if "chat_session" not in st.session_state:
    # Sohbet geçmişini burada başlatıyoruz.
    # Eğer ilk defa çalışıyorsa, başlangıç mesajını ekleyelim.
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        st.session_state.chat_history.append({"role": "model", "parts": ["Merhaba, size nasıl yardımcı olabilirim?"]})

    st.session_state.chat_session = st.session_state.gemini_model.start_chat(
        history=st.session_state.chat_history
    )

# Sohbet oturumunu kısayol olarak alalım
chat = st.session_state.chat_session

# --- Sohbet Geçmişini Streamlit Arayüzünde Gösterme ---
# Kullanıcının veya modelin attığı tüm mesajları göster
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["parts"][0])

# --- Kullanıcı Girişi ve Yanıt Üretme ---
# Streamlit'in sohbet giriş kutusundan kullanıcıdan mesaj al
if prompt := st.chat_input("Bir şeyler yazın..."):
    # Yeni bir mesaj geldiğinde bunu geçmişe ekle
    # SADECE prompt tanımlandığında ekliyoruz
    st.session_state.chat_history.append({"role": "user", "parts": [prompt]})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gemini'dan yanıt al
    with st.chat_message("model"):
        with st.spinner("Düşünüyorum..."):
            try:
                # Modeline yeni prompt'u gönder ve akışlı yanıt al
                response = chat.send_message(prompt, stream=True)
                full_response = ""
                for chunk in response:
                    full_response += chunk.text
                    st.markdown(full_response + "▌") # Yazarken göstermek için imleç ekle
                st.markdown(full_response)

                # Modelin tam yanıtını da geçmişe ekle
                st.session_state.chat_history.append({"role": "model", "parts": [full_response]})

            except Exception as e:
                st.error(f"Yanıt alınırken bir hata oluştu: {e}")
                st.markdown("Üzgünüm, şu anda yanıt veremiyorum. Lütfen tekrar deneyin.")
