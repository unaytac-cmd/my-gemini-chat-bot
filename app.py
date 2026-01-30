import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth

# --- 1. FIREBASE BAĞLANTISI ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase bağlantı hatası: {e}")
        st.stop()

# --- 2. SAYFA AYARLARI ---
st.set_page_config(page_title="Printnest AI", page_icon="💼")

if "user" not in st.session_state:
    st.session_state.user = None

# --- 3. GİRİŞ EKRANI ---
if st.session_state.user is None:
    st.title("💼 Printnest AI Giriş")
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        email = st.text_input("E-posta")
        password = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            try:
                user = auth.get_user_by_email(email)
                st.session_state.user = email
                st.rerun()
            except:
                st.error("Giriş başarısız.")
    
    with tab2:
        new_email = st.text_input("Yeni E-posta")
        new_pass = st.text_input("Yeni Şifre", type="password")
        if st.button("Kayıt Ol"):
            try:
                auth.create_user(email=new_email, password=new_pass)
                st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
            except Exception as e:
                st.error(f"Hata: {e}")
    st.stop()

# --- 4. GEMINI AYARLARI ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-2.5-flash")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 5. SIDEBAR ---
with st.sidebar:
    st.write(f"Giriş yapıldı: {st.session_state.user}")
    if st.button("Çıkış Yap"):
        st.session_state.user = None
        st.session_state.messages = []
        st.rerun()

# --- 6. CHAT ARAYÜZÜ ---
st.title("🚀 Printnest AI Çalışma Alanı")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Mesajınızı yazın..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = model.generate_content(prompt)
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})