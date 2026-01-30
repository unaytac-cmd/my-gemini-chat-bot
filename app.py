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

# --- 2. ŞİFRE DOĞRULAMA (API) ---
def verify_password(email, password):
    try:
        api_key = st.secrets["FIREBASE_WEB_API_KEY"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return res.json()["localId"]
        return None
    except:
        return None

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

# --- 4. SAYFA AYARLARI ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")

if "user" not in st.session_state: st.session_state.user = None
if "current_thread_id" not in st.session_state: st.session_state.current_thread_id = None

# --- 5. GİRİŞ EKRANI ---
if st.session_state.user is None:
    col1, col2 = st.columns([1.2, 1], gap="large")
    with col1:
        st.markdown("<br><br><h1>💼 Printnest</h1><h3>Kurumsal AI Portalı</h3>", unsafe_allow_html=True)
        st.info("Güvenli giriş yapıldıktan sonra asistanınız yüklenecektir.")
    with col2:
        with st.container(border=True):
            st.subheader("Giriş Yap")
            email = st.text_input("E-posta")
            password = st.text_input("Şifre", type="password")
            if st.button("Sisteme Gir", use_container_width=True, type="primary"):
                uid = verify_password(email, password)
                if uid:
                    st.session_state.user = {"email": email, "uid": uid}
                    st.session_state.current_thread_id = str(uuid.uuid4())
                    st.rerun()
                else: st.error("Hatalı e-posta veya şifre!")
    st.stop()

# --- 6. CHAT BOT YÜKLEME ---
user_id = st.session_state.user["uid"]
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-2.5-flash")

# Sidebar
with st.sidebar:
    st.markdown(f"### 💼 Printnest AI\n{st.session_state.user['email']}")
    if st.button("➕ Yeni Sohbet", use_container_width=True, type="primary"):
        st.session_state.current_thread_id = str(uuid.uuid4())
        st.session_state.chat_session = None; st.rerun()
    
    st.markdown("---")
    for t in get_user_threads(user_id):
        if st.button(f"💬 {t['title']}", key=t['id'], use_container_width=True):
            st.session_state.current_thread_id = t['id']
            st.session_state.chat_session = model.start_chat(history=load_messages_from_thread(user_id, t['id']))
            st.rerun()
    
    st.divider()
    if st.button("🚪 Çıkış"):
        st.session_state.user = None; st.rerun()

# Ana Ekran
if st.session_state.current_thread_id is None:
    st.session_state.current_thread_id = str(uuid.uuid4())

if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

# Sohbet geçmişini göster
for msg in st.session_state.chat_session.history:
    with st.chat_message("assistant" if msg.role == "model" else "user"):
        st.markdown(msg.parts[0].text)

if not st.session_state.chat_session.history:
    st.markdown("<h2 style='text-align:center;'>Merhaba! Nasıl yardımcı olabilirim?</h2>", unsafe_allow_html=True)

if prompt := st.chat_input("Buraya yazın..."):
    with st.chat_message("user"): st.markdown(prompt)
    save_message_to_db(user_id, st.session_state.current_thread_id, "user", prompt)
    
    response = st.session_state.chat_session.send_message(prompt)
    with st.chat_message("assistant"): st.markdown(response.text)
    save_message_to_db(user_id, st.session_state.current_thread_id, "model", response.text)