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
    [data-testid="stSidebar"] { background-color: #f8f9fa; padding-top: 0rem; }
    .stButton>button { border-radius: 8px; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar alt buton sabitleme */
    .sidebar-footer {
        position: fixed;
        bottom: 25px;
        width: 260px;
        background-color: #f8f9fa;
        padding-top: 10px;
    }
    
    /* Email ve Başlık Ortalama */
    .centered-text {
        text-align: center;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state.user = None
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# --- 3. GİRİŞ & KAYIT EKRANI ---
if st.session_state.user is None:
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown("<br><br># 💼 Printnest.com\n### Kurumsal Yapay Zeka Portalı", unsafe_allow_html=True)
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Personel Kaydı"])
        with tab1:
            email = st.text_input("Kurumsal E-posta", key="login_email")
            password = st.text_input("Şifre", type="password", key="login_pass")
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.user = {"email": email, "uid": user.uid}
                    st.session_state.current_thread_id = str(uuid.uuid4())
                    time.sleep(0.3); st.rerun()
                except: st.error("Hatalı giriş.")
        with tab2:
            n_email = st.text_input("Yeni E-posta", key="signup_email")
            n_pass = st.text_input("Yeni Şifre", type="password", key="signup_pass")
            access_key = st.text_input("Kurumsal Erişim Anahtarı", type="password")
            if st.button("Hesap Oluştur", use_container_width=True):
                m_key = st.secrets.get("CORPORATE_ACCESS_KEY")
                if access_key != m_key: st.error("Geçersiz Anahtar!")
                else:
                    try: 
                        auth.create_user(email=n_email, password=n_pass)
                        st.success("Kayıt başarılı!")
                    except Exception as e: st.error(f"Hata: {e}")
    st.stop()

# --- 4. YARDIMCI FONKSİYONLAR ---
def get_user_threads(user_id):
    threads = db.collection("users").document(user_id).collection("threads").order_by("updated_at", direction=firestore.Query.DESCENDING).limit(15).stream()
    return [{"id": t.id, "title": t.to_dict().get("title", "Yeni Sohbet")} for t in threads]

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
    # Başlık ve Email Ortalı
    st.markdown(f"""
        <div class='centered-text'>
            <h2 style='margin-bottom:0;'>💼 Printnest AI</h2>
            <p style='color: #555; font-size: 0.9rem;'>{st.session_state.user['email']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("➕ Yeni Sohbet", use_container_width=True, type="primary"):
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

    # Oturumu Kapat Butonu (En altta, chat bar ile hizalı)
    st.markdown("<div class='sidebar-footer'>", unsafe_allow_html=True)
    st.divider()
    if st.button("🚪 Oturumu Kapat", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 6. CHAT ALANI ---
if st.session_state.current_thread_id is None:
    st.session_state.current_thread_id = str(uuid.uuid4())
if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

# ESKİ GÜZEL KARŞILAMA YAZISI (GERİ GELDİ)
if not st.session_state.chat_session.history:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style='text-align: center;'>
            <h1 style='color: #0E1117; font-size: 3rem;'>Merhaba Printnest Ekibi! 👋</h1>
            <p style='font-size: 1.5rem; color: #555;'>
                Ben kurumsal asistanınız. Bugün iş süreçlerinizde size nasıl yardımcı olabilirim?
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )

for msg in st.session_state.chat_session.history:
    with st.chat_message("assistant" if msg.role == "model" else "user"):
        st.markdown(msg.parts[0].text)

if prompt := st.chat_input("Mesajınızı buraya yazın..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    save_message_to_db(user_id, st.session_state.current_thread_id, "user", prompt)
    res = st.session_state.chat_session.send_message(prompt)
    with st.chat_message("assistant"):
        st.markdown(res.text)
    save_message_to_db(user_id, st.session_state.current_thread_id, "model", res.text)