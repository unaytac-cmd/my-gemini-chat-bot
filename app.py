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

# --- 2. SAYFA AYARLARI ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")

# Session State Başlatma
if "user" not in st.session_state:
    st.session_state.user = None
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# --- 3. GİRİŞ EKRANI (SAFARI FIX) ---
if st.session_state.user is None:
    st.title("💼 Printnest Corporate AI")
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        email = st.text_input("E-posta", key="login_email")
        password = st.text_input("Şifre", type="password", key="login_pass")
        
        if st.button("Giriş", use_container_width=True):
            if email and password:
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.user = {"email": email, "uid": user.uid}
                    # Safari'nin state'i işlemesi için çok kısa bekleme ve rerun
                    time.sleep(0.2)
                    st.rerun() 
                except:
                    st.error("Giriş bilgileri hatalı veya kullanıcı bulunamadı.")
            else:
                st.warning("Lütfen tüm alanları doldurun.")
                
    with tab2:
        new_email = st.text_input("Yeni E-posta", key="signup_email")
        new_pass = st.text_input("Yeni Şifre", type="password", key="signup_pass")
        if st.button("Kayıt Ol", use_container_width=True):
            if len(new_pass) >= 6:
                try:
                    auth.create_user(email=new_email, password=new_pass)
                    st.success("Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
                except Exception as e:
                    st.error(f"Hata: {e}")