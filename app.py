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

# --- 2. ŞİFRE DOĞRULAMA ---
def verify_password(email, password):
    try:
        api_key = st.secrets["FIREBASE_WEB_API_KEY"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        res = requests.post(url, json=payload)
        return res.json()["localId"] if res.status_code == 200 else None
    except: return None

# --- 3. VERİTABANI YARDIMCILARI ---
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

# --- 4. SAYFA AYARLARI VE TASARIM ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    .stButton>button { border-radius: 8px; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stAppViewBlockContainer"] { opacity: 1 !important; }
    .feature-card {
        background-color: #f8f9fa; padding: 20px; border-radius: 12px;
        border-left: 5px solid #0e1117; margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

if "user" not in st.session_state: st.session_state.user = None
if "current_thread_id" not in st.session_state: st.session_state.current_thread_id = None

# --- 5. GİRİŞ EKRANI ---
if st.session_state.user is None:
    col1, col2 = st.columns([1.2, 1], gap="large")
    with col1:
        st.markdown("<h1 style='font-size: 3.5rem; margin-bottom:0;'>💼 Printnest</h1><h3 style='color: #444; margin-top:0;'>Kurumsal Yapay Zeka</h3>", unsafe_allow_html=True)
        st.markdown("<div class='feature-card'>🛡️ <strong>Güvenli:</strong> Firebase ile korunan veriler.</div>", unsafe_allow_html=True)
    with col2:
        with st.container(border=True):
            st.subheader("Giriş Yap")
            tab1, tab2 = st.tabs(["Anahtar Girişi", "Yeni Kayıt"])
            with tab1:
                e = st.text_input("E-posta", key="login_e")
                p = st.text_input("Şifre", type="password", key="login_p")
                if st.button("Giriş Yap", use_container_width=True, type="primary"):
                    uid = verify_password(e, p)
                    if uid:
                        st.session_state.user = {"email": e, "uid": uid}
                        st.session_state.current_thread_id = str(uuid.uuid4()); st.rerun()
                    else: st.error("Giriş başarısız!")
            with tab2:
                ne = st.text_input("E-posta")
                np = st.text_input("Şifre", type="password")
                ak = st.text_input("Erişim Anahtarı", type="password")
                if st.button("Kaydı Tamamla", use_container_width=True):
                    if ak == st.secrets.get("CORPORATE_ACCESS_KEY"):
                        try:
                            auth.create_user(email=ne, password=np)
                            st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
                        except Exception as e: st.error(f"Hata: {e}")
                    else: st.error("Erişim anahtarı geçersiz.")
    st.stop()

# --- 6. MODEL VE SİDEBAR ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# En sorunsuz çalışan model ismidir
model = genai.GenerativeModel("gemini-1.5-flash")

with st.sidebar:
    st.markdown("### 💼 Printnest AI")
    if st.button("➕ Yeni Sohbet", use_container_width=True, type="primary"):
        st.session_state.current_thread_id = str(uuid.uuid4())
        st.session_state.chat_session = None
        st.rerun()
    st.divider()
    for t in get_user_threads(st.session_state.user["uid"]):
        if st.button(f"💬 {t['title']}", key=t['id'], use_container_width=True):
            st.session_state.current_thread_id = t['id']
            st.session_state.chat_session = model.start_chat(history=load_messages_from_thread(st.session_state.user["uid"], t['id']))
            st.rerun()
    st.divider()
    if st.button("🚪 Oturumu Kapat", use_container_width=True):
        st.session_state.user = None; st.rerun()

# --- 7. CHAT EKRANI ---
if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

for msg in st.session_state.chat_session.history:
    with st.chat_message("assistant" if msg.role == "model" else "user"):
        st.markdown(msg.parts[0].text)

if prompt := st.chat_input("Mesajınızı yazın..."):
    st.chat_message("user").markdown(prompt)
    save_message_to_db(st.session_state.user["uid"], st.session_state.current_thread_id, "user", prompt)
    with st.chat_message("assistant"):
        try:
            res = st.session_state.chat_session.send_message(prompt)
            st.markdown(res.text)
            save_message_to_db(st.session_state.user["uid"], st.session_state.current_thread_id, "model", res.text)
        except Exception as e:
            st.error(f"Hata oluştu: {str(e)}")