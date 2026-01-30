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
            
            Printnest ailesine özel geliştirilmiş, iş süreçlerinizi hızlandıran akıllı asistan.
            
            **Hızlı Erişim:**
            * 🚀 Giriş yaptıktan sonra anında sohbete başlayabilirsiniz.
            * 🛡️ Personel kaydı için kurumsal erişim anahtarı gereklidir.
        """)

    with col2:
        st.subheader("Güvenli Giriş")
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Personel Kaydı"])
        
        with tab1:
            email = st.text_input("Kurumsal E-posta", key="login_email")
            password = st.text_input("Şifre", type="password", key="login_pass")
            
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                if email and password:
                    try:
                        user = auth.get_user_by_email(email)
                        st.session_state.user = {"email": email, "uid": user.uid}
                        st.session_state.current_thread_id = str(uuid.uuid4())
                        time.sleep(0.3)
                        st.rerun() 
                    except:
                        st.error("E-posta veya şifre hatalı.")
                else:
                    st.warning("Lütfen alanları doldurun.")
                    
        with tab2:
            n_email = st.text_input("Yeni E-posta", key="signup_email")
            n_pass = st.text_input("Yeni Şifre", type="password", key="signup_pass")
            access_key = st.text_input("Kurumsal Erişim Anahtarı", type="password")
            
            if st.button("Hesap Oluştur", use_container_width=True):
                master_key = st.secrets.get("CORPORATE_ACCESS_KEY")
                if access_key != master_key:
                    st.error("❌ Geçersiz Erişim Anahtarı!")
                elif len(n_pass) < 6:
                    st.warning("⚠️ Şifre en az 6 karakter olmalıdır.")
                elif n_email and n_pass:
                    try:
                        auth.create_user(email=n_email, password=n_pass)
                        st.success("✅ Kayıt başarılı! Giriş yapabilirsiniz.")
                    except Exception as e:
                        st.error(f"Hata: {e}")
    st.stop()

# --- 4. YARDIMCI FONKSİYONLAR ---
def get_user_threads(user_id):
    threads = db.collection("users").document(user_id).collection("threads").order_by("updated_at", direction=firestore.Query.DESCENDING).limit(15).stream()
    return [{"id": t.id, "title": t.to_dict().get("title", "Yeni Sohbet")} for t in threads]

def save_message_to_db(user_id, thread_id, role, text):
    thread_ref = db.collection("users").document(user_id).collection("threads").document(thread_id)
    thread_ref.collection("messages").add({"role": role, "text": text, "timestamp": datetime.now()})
    
    doc = thread_ref.get()
    if role == "user":
        if not doc.exists or "title" not in doc.to_dict() or doc.to_dict()["title"] == "Yeni Sohbet":
            title = text[:35] + "..." if len(text) > 35 else text
            thread_ref.set({"title": title, "updated_at": datetime.now()}, merge=True)
        else:
            thread_ref.update({"updated_at": datetime.now()})

def load_messages_from_thread(user_id, thread_id):
    messages = db.collection("users").document(user_id).collection("threads").document(thread_id).collection("messages").order_by("timestamp").stream()
    return [{"role": "user" if m.to_dict()["role"] == "user" else "model", "parts": [m.to_dict()["text"]]} for m in messages]

# --- 5. MODEL AYARLARI ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-2.5-flash")

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("Printnest AI")
    st.info(f"👤 {st.session_state.user['email']}")
    
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
        st.session_state.current_thread_id = str(uuid.uuid4())
        st.session_state.chat_session = None
        st.rerun()

    st.divider()
    st.subheader("📜 Geçmiş")
    user_id = st.session_state.user["uid"]
    for t in get_user_threads(user_id):
        if st.button(f"💬 {t['title']}", key=t['id'], use_container_width=True):
            st.session_state.current_thread_id = t['id']
            st.session_state.chat_session = model.start_chat(history=load_messages_from_thread(user_id, t['id']))
            st.rerun()

    st.divider()
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.user = None
        st.session_state.current_thread_id = None
        st.rerun()

# --- 7. CHAT EKRANI ---
if st.session_state.current_thread_id is None:
    st.session_state.current_thread_id = str(uuid.uuid4())

if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

# --- KARŞILAMA MESAJI (EĞER SOHBET YENİYSE) ---
if not st.session_state.chat_session.history:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style='text-align: center;'>
            <h1 style='color: #0E1117;'>Merhaba Printnest Ekibi! 👋</h1>
            <p style='font-size: 1.2rem; color: #555;'>
                Ben kurumsal asistanınız. Bugün iş süreçlerinizde size nasıl yardımcı olabilirim? <br>
                Rapor analizi, içerik üretimi veya teknik sorularınız için hazırım.
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

# Sohbet geçmişini ekrana bas
for msg in st.session_state.chat_session.history:
    with st.chat_message("assistant" if msg.role == "model" else "user"):
        st.markdown(msg.parts[0].text)

# Yeni mesaj girişi
if prompt := st.chat_input("Mesajınızı buraya yazın..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    save_message_to_db(user_id, st.session_state.current_thread_id, "user", prompt)
    
    response = st.session_state.chat_session.send_message(prompt)
    with st.chat_message("assistant"):
        st.markdown(response.text)
    save_message_to_db(user_id, st.session_state.current_thread_id, "model", response.text)