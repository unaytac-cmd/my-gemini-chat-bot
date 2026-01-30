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

# --- 3. GİRİŞ VE KAYIT EKRANI (BÖLÜNMÜŞ TASARIM) ---
if st.session_state.user is None:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("""
            # 💼 Printnest.com
            ### Kurumsal Yapay Zeka Portalı
            
            Printnest çalışanları için özel olarak geliştirilmiş Gemini tabanlı asistan.
            
            **Güvenlik Protokolü:**
            * 🔑 Kayıt işlemleri sadece kurumsal erişim anahtarı ile yapılabilir.
            * 🛡️ Verileriniz Firebase üzerinde güvenle saklanır.
            * 📜 Geçmiş konuşmalarınıza her yerden erişebilirsiniz.
            
            ---
            *Sorularınız için sistem yöneticisine başvurun.*
        """)

    with col2:
        st.subheader("Erişim Paneli")
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Personel Kaydı"])
        
        with tab1:
            email = st.text_input("E-posta", key="login_email")
            password = st.text_input("Şifre", type="password", key="login_pass")
            
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                if email and password:
                    try:
                        user = auth.get_user_by_email(email)
                        st.session_state.user = {"email": email, "uid": user.uid}
                        time.sleep(0.3) # Safari fix
                        st.rerun() 
                    except:
                        st.error("E-posta veya şifre hatalı.")
                else:
                    st.warning("Lütfen alanları doldurun.")
                    
        with tab2:
            n_email = st.text_input("Yeni E-posta", key="signup_email")
            n_pass = st.text_input("Yeni Şifre", type="password", key="signup_pass")
            # --- ÖZEL ERİŞİM ANAHTARI ---
            access_key = st.text_input("Kurumsal Erişim Anahtarı", type="password", help="Sadece Printnest yetkililerinden temine edilebilir.")
            
            if st.button("Hesap Oluştur", use_container_width=True):
                if access_key != st.secrets["CORPORATE_ACCESS_KEY"]:
                    st.error("❌ Geçersiz Erişim Anahtarı! Yetkisiz kayıt engellendi.")
                elif len(n_pass) < 6:
                    st.warning("⚠️ Şifre güvenliğiniz için en az 6 karakter olmalıdır.")
                elif n_email and n_pass:
                    try:
                        auth.create_user(email=n_email, password=n_pass)
                        st.success("✅ Kayıt başarılı! Giriş sekmesinden oturum açın.")
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Lütfen tüm bilgileri eksiksiz doldurun.")
    st.stop()

# --- 4. VERİTABANI FONKSİYONLARI ---
def get_user_threads(user_id):
    threads = db.collection("users").document(user_id).collection("threads").order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
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
    messages = db.collection("users").document(user_id).collection