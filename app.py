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

# --- 2. SAYFA VE SESSION AYARLARI ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# --- 3. GİRİŞ EKRANI (BUG FIX UYGULANDI) ---
if st.session_state.user is None:
    st.title("💼 Printnest Corporate AI")
    st.subheader("Kurumsal asistanınıza erişmek için giriş yapın.")
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        email = st.text_input("E-posta", key="login_email")
        password = st.text_input("Şifre", type="password", key="login_pass")
        
        if st.button("Giriş", use_container_width=True):
            if email and password:
                try:
                    # Kullanıcı doğrulaması
                    user = auth.get_user_by_email(email)
                    st.session_state.user = {"email": email, "uid": user.uid}
                    # BAŞARI: Sayfayı anında yenile (İkinci tıklamayı önler)
                    st.rerun() 
                except Exception:
                    st.error("Kullanıcı bulunamadı veya yetkisiz erişim. Lütfen bilgilerinizi kontrol edin.")
            else:
                st.warning("E-posta ve şifre alanlarını doldurun.")
                
    with tab2:
        new_email = st.text_input("Yeni E-posta", key="signup_email")
        new_pass = st.text_input("Yeni Şifre", type="password", key="signup_pass")
        if st.button("Kayıt Ol", use_container_width=True):
            if new_email and len(new_pass) >= 6:
                try:
                    auth.create_user(email=new_email, password=new_pass)
                    st.success("Kayıt başarılı! Giriş sekmesine dönerek oturum açabilirsiniz.")
                except Exception as e:
                    st.error(f"Kayıt sırasında bir hata oluştu: {e}")
            else:
                st.warning("Şifre en az 6 karakter olmalıdır.")
    st.stop()

# --- 4. YARDIMCI FONKSİYONLAR (THREAD & PERSISTENCE) ---

def get_user_threads(user_id):
    """Eski konuşma başlıklarını listeler."""
    threads = db.collection("users").document(user_id).collection("threads").order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
    return [{"id": t.id, "title": t.to_dict().get("title", "Yeni Sohbet")} for t in threads]

def save_message_to_db(user_id, thread_id, role, text):
    """Mesajı kaydeder ve ilk mesajı başlık yapar."""
    thread_ref = db.collection("users").document(user_id).collection("threads").document(thread_id)
    
    # Mesajı ekle
    thread_ref.collection("messages").add({
        "role": role,
        "text": text,
        "timestamp": datetime.now()
    })
    
    # Başlık oluşturma (Sadece ilk kullanıcı mesajında)
    doc = thread_ref.get()
    if role == "user":
        if not doc.exists or "title" not in doc.to_dict() or doc.to_dict()["title"] == "Yeni Sohbet":
            title = text[:40] + "..." if len(text) > 40 else text
            thread_ref.set({"title": title, "updated_at": datetime.now()}, merge=True)
        else:
            thread_ref.update({"updated_at": datetime.now()})

def load_messages_from_thread(user_id, thread_id):
    """Seçili konuşmanın geçmişini çeker."""
    messages = db.collection("users").document(user_id).collection("threads").document(thread_id).collection("messages").order_by("timestamp").stream()
    return [{"role": "user" if m.to_dict()["role"] == "user" else "model", "parts": [m.to_dict()["text"]]} for m in messages]

# --- 5. MODEL AYARLARI ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-2.5-flash")

# --- 6. SIDEBAR (HISTORY & LOGOUT) ---
with st.sidebar:
    st.title("Printnest AI")
    st.write(f"👤 **{st.session_state.user['email']}**")
    
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
        st.session_state.current_thread_id = str(uuid.uuid4())
        st.session_state.chat_session = model.start_chat(history=[])
        st.rerun()

    st.divider()
    st.subheader("📜 Sohbet Geçmişi")
    
    threads = get_user_threads(st.session_state.user["uid"])
    for t in threads:
        if st.button(f"💬 {t['title']}", key=t['id'], use_container_width=True):
            st.session_state.current_thread_id = t['id']
            history = load_messages_from_thread(st.session_state.user["uid"], t['id'])
            st.session_state.chat_session = model.start_chat(history=history)
            st.rerun()

    st.divider()
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.user = None
        st.session_state.current_thread_id = None
        st.rerun()

# --- 7. CHAT UI ---
if st.session_state.current_thread_id is None:
    st.info("Çalışmaya başlamak için lütfen soldan bir sohbet seçin veya yeni bir tane başlatın.")
    st.stop()

st.title("🚀 Kurumsal Çalışma Alanı")

if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

# Sohbeti Görüntüle
for msg in st.session_state.chat_session.history:
    role = "assistant" if msg.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(msg.parts[0].text)

# Input
if prompt := st.chat_input("Bir soru sorun..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # DB Kaydı
    save_message_to_db(st.session_state.user["uid"], st.session_state.current_thread_id, "user", prompt)
    
    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(prompt)
        st.markdown(response.text)
        save_message_to_db(st.session_state.user["uid"], st.session_state.current_thread_id, "model", response.text)