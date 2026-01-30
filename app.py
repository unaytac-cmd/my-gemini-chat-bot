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
    
    /* Giriş Sayfası Hizalama */
    .centered-header { text-align: center; margin-bottom: 20px; }
    
    .feature-card {
        background-color: #f8f9fa;
        padding: 18px;
        border-radius: 12px;
        border-left: 4px solid #0e1117;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Kolonları dikeyde ortala */
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
    st.markdown("<div style='padding-top: 8vh;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.2, 1], gap="large")
    
    with col1:
        st.markdown("<h1 style='font-size: 3.5rem; margin-bottom:0;'>💼 Printnest</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #444; margin-top:0;'>Kurumsal Yapay Zeka Portalı</h3>", unsafe_allow_html=True)
        st.write("İş süreçlerinizi modernize eden, verilerinizi koruyan ve size özel çözümler üreten akıllı asistanınıza hoş geldiniz.")
        
        st.markdown("""
        <div class="feature-card">
            <span style='font-size: 1.2rem;'>🚀</span> <strong>Hızlı Erişim</strong><br>
            <small style='color: #666;'>Gemini 2.5 Flash ile anlık kurumsal yanıtlar.</small>
        </div>
        <div class="feature-card">
            <span style='font-size: 1.2rem;'>🛡️</span> <strong>Güvenli Veri</strong><br>
            <small style='color: #666;'>Firebase altyapısıyla şifrelenmiş özel veri koruması.</small>
        </div>
        <div class="feature-card">
            <span style='font-size: 1.2rem;'>📜</span> <strong>Sınırsız Bellek</strong><br>
            <small style='color: #666;'>Tüm geçmiş yazışmalarınız her an yanınızda.</small>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.subheader("Güvenli Erişim")
            tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
            
            with tab1:
                email = st.text_input("E-posta", key="login_email")
                password = st.text_input("Şifre", type="password", key="login_pass")
                if st.button("Sisteme Giriş Yap", use_container_width=True, type="primary"):
                    if email and password:
                        try:
                            user_data = auth.get_user_by_email(email)
                            st.session_state.user = {"email": email, "uid": user_data.uid}
                            st.session_state.current_thread_id = str(uuid.uuid4())
                            time.sleep(0.3)
                            st.rerun()
                        except:
                            st.error("E-posta veya şifre hatalı!")
                    else:
                        st.warning("Lütfen alanları doldurun.")
            
            with tab2:
                n_email = st.text_input("Kurumsal E-posta", key="signup_email")
                n_pass = st.text_input("Şifre Belirleyin", type="password", key="signup_pass")
                access_key = st.text_input("Erişim Anahtarı", type="password")
                if st.button("Hesap Oluştur", use_container_width=True):
                    m_key = st.secrets.get("CORPORATE_ACCESS_KEY")
                    if access_key != m_key:
                        st.error("Geçersiz Erişim Anahtarı!")
                    elif len(n_pass) < 6:
                        st.warning("Şifre en az 6 karakter olmalıdır.")
                    else:
                        try:
                            auth.create_user(email=n_email, password=n_pass)
                            st.success("Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
                        except Exception as e:
                            st.error(f"Hata: {e}")
    st.stop()

# --- 4. YARDIMCI FONKSİYONLAR ---
def get_user_threads(user_id):
    return [{"id": t.id, "title": t.to_dict().get("title", "Yeni Sohbet")} for t in db.collection("users").document(user_id).collection("threads").order_by("updated_at", direction=firestore.Query.DESCENDING).limit(15).stream()]

def save_message_to_db(user_id, thread_id, role, text):
    t_ref = db.collection("users").document(user_id).collection("threads").document(thread_id)
    t_ref.collection("messages").add({"role": role, "text": text, "timestamp": datetime.now()})
    if role == "user":
        title = text[:30] + "..." if len(text) > 30 else text
        t_ref.set({"title": title, "updated_at": datetime.now()}, merge=True)

def load_messages_from_thread(user_id, thread_id):
    msgs = db.collection("users").document(user_id).collection("threads").document(thread_id).collection("messages").order_by("timestamp").stream()
    return [{"role": "user" if m.to_dict()["role"] == "user" else "model", "parts": [{"text": m.to_dict()["text"]}]} for m in msgs]

# --- 5. SIDEBAR & MODEL ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-2.5-flash")

with st.sidebar:
    st.markdown(f"<div class='centered-header'><h2>💼 Printnest AI</h2><p>{st.session_state.user['email']}</p></div>", unsafe_allow_html=True)
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True, type="primary"):
        st.session_state.current_thread_id = str(uuid.uuid4())
        st.session_state.chat_session = None
        st.rerun()
    st.markdown("---")
    st.markdown("#### 📜 Sohbet Geçmişi")
    user_id = st.session_state.user["uid"]
    for t in get_user_threads(user_id):
        if st.button(f"💬 {t['title']}", key=t['id'], use_container_width=True):
            st.session_state.current_thread_id = t['id']
            st.session_state.chat_session = model.start_chat(history=load_messages_from_thread(user_id, t['id']))
            st.rerun()
    st.divider()
    if st.button("🚪 Oturumu Kapat", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# --- 6. CHAT ALANI ---
if st.session_state.current_thread_id is None: st.session_state.current_thread_id = str(uuid.uuid4())
if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

if not st.session_state.chat_session.history:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center;'><h1 style='font-size: 3rem;'>Merhaba Printnest Ekibi! 👋</h1><p style='font-size: 1.5rem; color: #555;'>Bugün size nasıl yardımcı olabilirim?</p></div>", unsafe_allow_html=True)

for msg in st.session_state.chat_session.history:
    with st.chat_message("assistant" if msg.role == "model" else "user"): st.markdown(msg.parts[0].text)

if prompt := st.chat_input("Mesajınızı buraya yazın..."):
    with st.chat_message("user"): st.markdown(prompt)
    save_message_to_db(user_id, st.session_state.current_thread_id, "user", prompt)
    res = st.session_state.chat_session.send_message(prompt)
    with st.chat_message("assistant"): st.markdown(res.text)
    save_message_to_db(user_id, st.session_state.current_thread_id, "model", res.text)