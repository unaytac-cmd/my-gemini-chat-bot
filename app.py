import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
import uuid
from datetime import datetime
import time

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

# --- 2. SAYFA VE SESSION AYARLARI ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# --- 3. GİRİŞ VE KAYIT EKRANI ---
if st.session_state.user is None:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("""
            # 💼 Printnest.com
            ### Kurumsal Yapay Zeka Portalı
            
            İş süreçlerinizi optimize eden Gemini tabanlı akıllı asistan.
            
            **Erişim Kuralları:**
            * 🔑 **Personel Kaydı:** Sadece kurumsal erişim anahtarı ile mümkündür.
            * 🛡️ **Güvenlik:** Tüm veriler şifrelenmiş altyapıda saklanır.
            * 📜 **Bellek:** Geçmiş konuşmalarınız otomatik yedeklenir.
            
            ---
            *Erişim anahtarını yöneticinizden talep edin.*
        """)

    with col2:
        st.subheader("Güvenli Giriş")
        tab1, tab2 = st.