import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
import uuid
from datetime import datetime
import time
import requests

# --- 1. FIREBASE BAĞLANTISI ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase bağlantı hatası: {e}")
        st.stop()

db = firestore.client()

# --- 2. ŞİFRE DOĞRULAMA FONKSİYONU ---
def verify_password(email, password):
    try:
        api_key = st.secrets["FIREBASE_WEB_API_KEY"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        res = requests.post(url, json=payload)
        res_data = res.json()
        if res.status_code == 200:
            return res_data["localId"]
        else:
            return None
    except Exception:
        return None

# --- 3. SAYFA AYARLARI ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

# --- 4. GİRİŞ & KAYIT EKRANI ---
if st.session_state.user is None:
    col1, col2 = st.columns([1.2, 1], gap="large")
    with col1:
        st.markdown("<br><br><h1>💼 Printnest</h1><h3>Kurumsal Yapay Zeka Portalı</h3>", unsafe_allow_html=True)
        st.info("Güvenliğiniz için gerçek şifre doğrulaması aktif edildi.")
    with col2:
        with st.container(border=True):
            st.subheader("Güvenli Erişim")
            tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
            with tab1:
                email = st.text_input("E-posta")
                password = st.text_input("Şifre", type="password")
                if st.button("Giriş Yap", use_container_width=True, type="primary"):
                    uid = verify_password(email, password)
                    if uid:
                        st.session_state.user = {"email": email, "uid": uid}
                        st.session_state.current_thread_id = str(uuid.uuid4())
                        st.rerun()
                    else:
                        st.error("E-posta veya şifre hatalı!")
            with tab2:
                # Kayıt işlemleri aynı kalacak...
                pass
    st.stop()