import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv # Sadece yerel geliştirme için, Streamlit Cloud'da kullanılmayacak

# --- Streamlit Sayfa Yapılandırması ---
st.set_page_config(
    page_title="ESIMDE ESIM",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("⚡ ESIMI COK SEVIYORUM")
st.write("Merhaba! Ben Google'ın Gemini Flash 2.5 modelini kullanan bir sohbet botuyum. Sizinle yapılan önceki konuşmaları hatırlayabilirim.")

# --- API Anahtarını Yükleme ve GenAI Kütüphanesini Yapılandırma ---
# Streamlit Cloud'da 'st.secrets' kullanılarak güvenli bir şekilde anahtar alınır.
# Yerel geliştirme ortamında ise '.env' dosyasından okunur.
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        # Yerel '.env' dosyasını yükle
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            st.error("Gemini API Anahtarı bulunamadı.")
            st.warning("Lütfen API anahtarınızı aşağıdaki konumlardan birine ekleyin:")
            st.code("1. Yerel geliştirme için: Proje kök dizinindeki '.env' dosyasına 'GOOGLE_API_KEY=\"SİZİN_ANAHTARINIZ\"' şeklinde.")
            st.code("2. Streamlit Cloud için: Uygulamanızı dağıtırken 'Advanced settings' altındaki 'Secrets' bölümüne 'GOOGLE_API_KEY=\"SİZİN_ANAHTARINIZ\"' şeklinde.")
            st.stop() # Anahtar yoksa uygulamayı durdur

    genai.configure(api_key=api_key)

except Exception as e:
    st.error(f"API anahtarı yapılandırma hatası oluştu: {e}")
    st.stop()

# --- Sohbet Geçmişini Başlatma (Hafıza Mekanizması) ---
# Streamlit'in session_state'i, her tarayıcı oturumu için özel ve kalıcı veri saklar.
# Bu sayede, kullanıcı tarayıcıyı kapatana veya yenileyene kadar bot geçmişi hatırlar.
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    # Botun ilk mesajını sohbet geçmişine ekleyelim
    st.session_state.chat_history.append({"role": "model", "parts": ["Merhaba, size nasıl yardımcı olabilirim?"]})

# --- Gemini GenerativeModel'i Ayarlama ---
# Burada kullanılacak Gemini modelini belirtiyoruz.
# `gemini-flash-2.5` modelini kullanmak için bu adı güncelliyoruz.
# Modelin sohbet geçmişini (history) almasını sağlıyoruz ki bağlamı koruyabilsin.
try:
    model = genai.GenerativeModel(
        model_name="models/gemini-2.5-flash" # Kullanılacak modelin adı
        # İsteğe bağlı: Daha fazla kontrol için 'generation_config' ve 'safety_settings' eklenebilir.
        # generation_config={
        #     "temperature": 0.9,      # Yaratıcılık derecesi (0.0-1.0)
        #     "top_p": 1,              # Top-P örnekleme
        #     "top_k": 1,              # Top-K örnekleme
        #     "max_output_tokens": 2048 # Maksimum yanıt uzunluğu
        # },
        # safety_settings=[
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        # ]
    )
    # Model ile bir sohbet oturumu başlatıyoruz ve mevcut geçmişi sağlıyoruz.
    chat = model.start_chat(history=st.session_state.chat_history)

except Exception as e:
    st.error(f"Gemini modeli başlatılırken bir hata oluştu: {e}")
    st.markdown("Lütfen API anahtarınızın geçerli olduğundan ve 'gemini-flash-2.5' modeline erişim izninizin olduğundan emin olun.")
    st.stop() # Model başlatılamazsa uygulamayı durdur

# --- Sohbet Geçmişini Streamlit Arayüzünde Gösterme ---
# session_state'deki her mesajı, uygun rol (user/model) ile Streamlit chat_message bileşeniyle göster.
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["parts"][0])

# --- Kullanıcı Girişi ve Yanıt Üretme ---
# Kullanıcıdan mesaj almak için Streamlit'in entegre sohbet giriş kutusunu kullanırız.
if prompt := st.chat_input("Bir şeyler yazın..."):
    # Kullanıcının mesajını sohbet geçmişine ekle ve arayüzde göster
    st.session_state.chat_history.append({"role": "user", "parts": [prompt]})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gemini'dan yanıt al ve arayüzde göster
    with st.chat_message("model"):
        with st.spinner("Düşünüyorum..."): # Yanıt gelene kadar kullanıcıya bekleme mesajı göster
            try:
                # Gemini modeline kullanıcı mesajını gönder ve akışlı (stream=True) yanıt al.
                # Akışlı yanıt, mesajın karakter karakter veya kelime kelime gelmesini sağlar,
                # bu da kullanıcı deneyimini iyileştirir.
                response = chat.send_message(prompt, stream=True)
                full_response = ""
                # Akışlı yanıtın parçalarını birleştir ve arayüzde göster
                for chunk in response:
                    full_response += chunk.text
                    st.markdown(full_response + "▌") # Yazarken göstermek için imleç ekle
                st.markdown(full_response) # Tam yanıtı göster

                # Modelin tam yanıtını sohbet geçmişine ekle
                st.session_state.chat_history.append({"role": "model", "parts": [full_response]})

            except Exception as e:
                st.error(f"Yanıt alınırken bir hata oluştu: {e}")
                st.markdown("Üzgünüm, şu anda yanıt veremiyorum. Lütfen tekrar deneyin veya API anahtarınızı kontrol edin.")
