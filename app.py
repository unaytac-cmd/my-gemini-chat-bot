import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
import uuid
from datetime import datetime
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

# --- 2. ŞİFRE DOĞRULAMA (API) ---
def verify_password(email, password):
    try:
        api_key = st.secrets["FIREBASE_WEB_API_KEY"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        res = requests.post(url, json=payload)
        return res.json()["localId"] if res.status_code == 200 else None
    except: return None

# --- 3. YARDIMCI FONKSİYONLAR ---
def get_user_threads(user_id):
    try:
        threads = db.collection("users").document(user_id).collection("threads").order_by("updated_at", direction=firestore.Query.DESCENDING).limit(15).stream()
        return [{"id": t.id, "title": t.to_dict().get("title", "Yeni Sohbet")} for t in threads]
    except: return []

def load_messages_from_thread(user_id, thread_id):
    try:
        msgs = db.collection("users").document(user_id).collection("threads").document(thread_id).collection("messages").order_by("timestamp").stream()
        return [{"role": "user" if m.to_dict()["role"] == "user" else "model", "parts": [{"text": m.to_dict()["text"]}]} for m in msgs]
    except: return []

def save_message_to_db(user_id, thread_id, role, text):
    t_ref = db.collection("users").document(user_id).collection("threads").document(thread_id)
    t_ref.collection("messages").add({"role": role, "text": text, "timestamp": datetime.now()})
    if role == "user":
        title = text[:30] + "..." if len(text) > 30 else text
        t_ref.set({"title": title, "updated_at": datetime.now()}, merge=True)

# --- 4. SAYFA AYARLARI VE CSS ---
st.set_page_config(page_title="Printnest AI - Gemini 3", page_icon="💼", layout="wide")
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #f8f9fa; padding-top: 1rem; }
    .stButton>button { border-radius: 8px; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stAppViewBlockContainer"] { opacity: 1 !important; }
    .feature-card {
        background-color: #f8f9fa; padding: 20px; border-radius: 12px;
        border-left: 5px solid #0e1117; margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); font-size: 1.1rem;
    }
    .centered-text { text-align: center; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

if "user" not in st.session_state: st.session_state.user = None
if "current_thread_id" not in st.session_state: st.session_state.current_thread_id = None

# --- 5. GİRİŞ & KAYIT EKRANI ---
if st.session_state.user is None:
    st.markdown("<div style='padding-top: 8vh;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1.2, 1], gap="large")
    with col1:
        st.markdown("<h1 style='font-size: 3.5rem; margin-bottom:0;'>💼 Printnest</h1><h3 style='color: #444; margin-top:0;'>Gemini 3 Destekli Portalı</h3>", unsafe_allow_html=True)
        st.markdown("<div class='feature-card'>🌍 <strong>Canlı Veri:</strong> İnternet erişimi ile anlık borsa ve haberler.</div>", unsafe_allow_html=True)
        st.markdown("<div class='feature-card'>🛡️ <strong>Güvenli Panel:</strong> Firebase şifrelemeli giriş.</div>", unsafe_allow_html=True)
    with col2:
        with st.container(border=True):
            st.subheader("Kurumsal Erişim")
            tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
            with tab1:
                email = st.text_input("E-posta", key="login_email")
                password = st.text_input("Şifre", type="password", key="login_pass")
                if st.button("Giriş", use_container_width=True, type="primary"):
                    uid = verify_password(email, password)
                    if uid:
                        st.session_state.user = {"email": email, "uid": uid}
                        st.session_state.current_thread_id = str(uuid.uuid4()); st.rerun()
                    else: st.error("Hatalı bilgiler!")
            with tab2:
                n_email = st.text_input("Yeni E-posta", key="signup_email")
                n_pass = st.text_input("Yeni Şifre", type="password", key="signup_pass")
                a_key = st.text_input("Erişim Anahtarı", type="password")
                if st.button("Kayıt Ol", use_container_width=True):
                    if a_key == st.secrets.get("CORPORATE_ACCESS_KEY") and len(n_pass) >= 6:
                        try:
                            auth.create_user(email=n_email, password=n_pass)
                            st.success("Başarılı! Giriş yapabilirsiniz.")
                        except Exception as e: st.error(f"Hata: {e}")
                    else: st.error("Geçersiz anahtar!")
    st.stop()

# --- 6. SIDEBAR VE GEMINI 3 MODELİ ---
user_id = st.session_state.user["uid"]
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Gemini 3 Flash varyantı ve yerleşik Google Search aracı
model = genai.GenerativeModel(
    model_name="gemini-3-flash",
    tools=[{"google_search": {}}]
)

with st.sidebar:
    st.markdown(f"<div class='centered-text'><h2>💼 Printnest</h2><p>{st.session_state.user['email']}</p></div>", unsafe_allow_html=True)
    if st.button("➕ Yeni Sohbet", use_container_width=True, type="primary"):
        st.session_state.current_thread_id = str(uuid.uuid4()); st.session_state.chat_session = None; st.rerun()
    st.markdown("---")
    for t in get_user_threads(user_id):
        if st.button(f"💬 {t['title']}", key=t['id'], use_container_width=True):
            st.session_state.current_thread_id = t['id']
            st.session_state.chat_session = model.start_chat(history=load_messages_from_thread(user_id, t['id']))
            st.rerun()
    st.divider()
    if st.button("🚪 Çıkış", use_container_width=True):
        st.session_state.user = None; st.rerun()

# --- 7. ANA CHAT EKRANI ---
if st.session_state.current_thread_id is None:
    st.session_state.current_thread_id = str(uuid.uuid4())
if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

if not st.session_state.chat_session.history:
    st.markdown("<br><br><div style='text-align: center;'><h1>Merhaba! 👋</h1><p>Gemini 3 Flash ile canlı verilere erişebilirim.</p></div>", unsafe_allow_html=True)

for msg in st.session_state.chat_session.history:
    with st.chat_message("assistant" if msg.role == "model" else "user"): st.markdown(msg.parts[0].text)

if prompt := st.chat_input("Bir şey sorun..."):
    with st.chat_message("user"): st.markdown(prompt)
    save_message_to_db(user_id, st.session_state.current_thread_id, "user", prompt)
    with st.chat_message("assistant"):
        with st.spinner("Gemini 3 analiz ediyor..."):
            res = st.session_state.chat_session.send_message(prompt)
            st.markdown(res.text)
            save_message_to_db(user_id, st.session_state.current_thread_id, "model", res.text)