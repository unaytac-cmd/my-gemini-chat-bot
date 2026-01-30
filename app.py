import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
import uuid
from datetime import datetime

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

if "user" not in st.session_state:
    st.session_state.user = None
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# --- 3. GİRİŞ EKRANI (BUG FIX BURADA) ---
if st.session_state.user is None:
    st.title("💼 Printnest Corporate AI")
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        email = st.text_input("E-posta", key="l_email")
        password = st.text_input("Şifre", type="password", key="l_pass")
        
        if st.button("Giriş", use_container_width=True):
            if email and password:
                try:
                    # Kullanıcı doğrula
                    user = auth.get_user_by_email(email)
                    # Oturumu kaydet
                    st.session_state.user = {"email": email, "uid": user.uid}
                    # ÖNEMLİ: Sayfayı anında yenile (İkinci tıklamayı önleyen satır)
                    st.rerun() 
                except:
                    st.error("Kullanıcı bulunamadı veya yetkisiz erişim.")
            else:
                st.warning("Lütfen bilgilerinizi girin.")
    
    with tab2:
        n_email = st.text_input("Yeni E-posta", key="s_email")
        n_pass = st.text_input("Yeni Şifre", type="password", key="s_pass")
        if st.button("Kayıt Ol", use_container_width=True):
            try:
                auth.create_user(email=n_email, password=n_pass)
                st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
            except Exception as e:
                st.error(f"Hata: {e}")
    st.stop()

# --- 4. YARDIMCI FONKSİYONLAR (THREAD SİSTEMİ) ---

def get_user_threads(user_id):
    threads = db.collection("users").document(user_id).collection("threads").order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
    return [{"id": t.id, "title": t.to_dict().get("title", "Yeni Sohbet")} for t in threads]

def save_message_to_db(user_id, thread_id, role, text):
    thread_ref = db.collection("users").document(user_id).collection("threads").document(thread_id)
    thread_ref.collection("messages").add({"role": role, "text": text, "timestamp": datetime.now()})
    
    doc = thread_ref.get()
    if role == "user":
        # İlk soruyu başlık yapma mantığı
        if not doc.exists or "title" not in doc.to_dict() or doc.to_dict()["title"] == "Yeni Sohbet":
            title = text[:40] + "..." if len(text) > 40 else text
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
    st.write(f"📧 **{st.session_state.user['email']}**")
    
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
        st.session_state.current_thread_id = str(uuid.uuid4())
        st.session_state.chat_session = model.start_chat(history=[])
        st.rerun()

    st.divider()
    st.subheader("📜 Sohbet Geçmişi")
    for t in get_user_threads(st.session_state.user["uid"]):
        if st.button(f"💬 {t['title']}", key=t['id'], use_container_width=True):
            st.session_state.current_thread_id = t['id']
            st.session_state.chat_session = model.start_chat(history=load_messages_from_thread(st.session_state.user["uid"], t['id']))
            st.rerun()

    st.divider()
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.user = None
        st.session_state.current_thread_id = None
        st.rerun()

# --- 7. CHAT UI ---
if st.session_state.current_thread_id is None:
    st.info("Lütfen soldan bir sohbet seçin veya yeni bir sohbet başlatın.")
    st.stop()

st.title("🚀 Çalışma Alanı")

if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

for msg in st.session_state.chat_session.history:
    with st.chat_message("assistant" if msg.role == "model" else "user"):
        st.markdown(msg.parts[0].text)

if prompt := st.chat_input("Mesajınızı yazın..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    save_message_to_db(st.session_state.user["uid"], st.session_state.current_thread_id, "user", prompt)
    
    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(prompt)
        st.markdown(response.text)
        save_message_to_db(st.session_state.user["uid"], st.session_state.current_thread_id, "model", response.text)