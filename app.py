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

# --- 2. SAYFA VE CSS AYARLARI ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")

st.markdown("""
    <style>
    /* Sidebar Stilleri */
    [data-testid="stSidebar"] { background-color: #f8f9fa; padding-top: 1rem; }
    .stButton>button { border-radius: 8px; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Giriş Sayfası Hizalama Sorununu Çözen CSS */
    .login-container {
        display: flex;
        align-items: center; /* Dikeyde ortala */
        justify-content: center;
        min-height: 80vh; /* Sayfa yüksekliğinin %80'ini kapla */
    }
    .centered-header { text-align: center; margin-bottom: 20px; }
    
    .feature-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #0e1117;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Kolon boşluklarını ayarla */
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state.user = None
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# --- 3. GİRİŞ & KAYIT EKRANI ---
if st.session_state.user is None:
    # Sayfayı dikeyde ortalamak için boşluk bırakıyoruz
    st.markdown("<div style='padding-top: 5vh;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("<h1 style='font-size: 3.5rem; margin-bottom:0;'>💼 Printnest</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #444; margin-top:0;'>Kurumsal Yapay Zeka Portalı</h3>", unsafe_allow_html=True)
        st.write("İş süreçlerinizi modernize eden, verilerinizi koruyan ve size özel çözümler üreten akıllı asistanınıza hoş geldiniz.")
        
        st.markdown("""
        <div class="feature-card">
            <span style='font-size: 1.2rem;'>🚀</span> <strong>Hızlı Erişim</strong><br>
            <small style='color: #666;'>Gemini 2.5 Flash ile anlık yanıtlar.</small>
        </div>
        <div class="feature-card">
            <span style='font-size: 1.2rem;'>🛡️</span> <strong>Güvenli Veri</strong><br>
            <small style='color: #666;'>Kurumsal gizlilik standartlarında koruma.</small>
        </div>
        <div class="feature-card">
            <span style='font-size: 1.2rem;'>📜</span> <strong>Sınırsız Bellek</strong><br>
            <small style='color: #666;'>Tüm geçmişiniz tek tıkla elinizin altında.</small>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Sağ tarafı kutu içine alarak daha dengeli durmasını sağlıyoruz
        with st.container(border=True):
            st.subheader("Giriş Paneli")
            tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
            
            with tab1:
                email = st.text_input("E-posta", key="login_email")
                password = st.text_input("Şifre", type="password", key="login_pass")
                if st.button("Giriş Yap", use_container_width=True, type="primary"):
                    if email and password:
                        try:
                            user = auth.get_user