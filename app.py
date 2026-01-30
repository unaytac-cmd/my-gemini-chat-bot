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

# --- 3. GİRİŞ VE KAYIT EKRANI (DÜZELTİLMİŞ FORM YAPISI) ---
if st.session_state.user is None:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("""
            # 💼 Printnest.com
            ### Kurumsal Yapay Zeka Portalı
            
            Printnest çalışanları için optimize edilmiş güvenli asistan.
            
            **Sistem Özellikleri:**
            * 🔑 **Güvenli Kayıt:** Kurumsal erişim anahtarı zorunluluğu.
            * 🛡️ **Veri Gizliliği:** Sohbetleriniz size özeldir.
            * 📜 **Akıllı Bellek:** Önceki konuşmalarınıza anında erişin.
        """)

    with col2:
        st.subheader("Erişim Paneli")
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Personel Kaydı"])
        
        with tab1:
            # st.form kullanarak girişi izole ediyoruz (Hatalı giriş bug'ını çözer)
            with st.form("login_form"):
                email = st.text_input("Kurumsal E-posta")
                password = st.text_input("Şifre", type="password")
                submit_button = st.form_submit_button("Sisteme Giriş Yap", use_container_width=True, type="primary")
                
                if submit_button:
                    if email and password:
                        try:
                            # Kullanıcıyı Firebase'den çek
                            user = auth.get_user_by_email(email)
                            # Giriş başarılıysa session'ı güncelle
                            st.session_state.user = {"email": email, "uid": user.uid}
                            st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception:
                            # HATA DURUMUNDA SESSION'I SIFIRLA
                            st.session_state.user = None