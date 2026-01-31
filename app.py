import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
import uuid
from datetime import datetime
import requests
import json

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

# --- 2. SERPER.DEV ARAMA FONKSİYONU ---
def get_live_search(query):
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "gl": "tr", # Türkiye lokasyonu
        "hl": "tr"  # Türkçe dil desteği
    })
    headers = {
        'X-API-KEY': st.secrets["SERPER_API_KEY"],
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        results = response.json()
        
        # Arama sonuçlarından snippet'leri topluyoruz
        search_data = ""
        if "organic" in results:
            for item in results["organic"][:4]: # En alakalı ilk 4 sonuç
                search_data += f"\nKaynak: {item['title']}\nBilgi: {item['snippet']}\n"
        return search_data if search_data else "İnternette güncel bilgi bulunamadı."
    except Exception as e:
        return f"Arama hatası: {str(e)}"

# --- 3. ŞİFRE DOĞRULAMA ---
def verify_password(email, password):
    try:
        api_key = st.secrets["FIREBASE_WEB_API_KEY"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        res = requests.post(url, json=payload)
        return res.json()["localId"] if res.status_code == 200 else None
    except: return None

# --- 4. VERİTABANI YARDIMCILARI ---
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

# --- 5. TASARIM ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")
st.markdown("<style>[data-testid='stAppViewBlockContainer'] { opacity: 1 !important; }</style>", unsafe_allow_html=True)

if "user" not in st.session_state: st.session_state.user = None
if "current_thread_id" not in st.session_state: st.session_state.current_thread_id = None

# --- 6. GİRİŞ EKRANI ---
if st.session_state.user is None:
    # (Önceki giriş ekranı kodun buraya gelecek - aynı kalıyor)
    col1, col2 = st.columns([1.2, 1], gap="large")
    with col1:
        st.markdown("<h1 style='font-size: 3.5rem;'>💼 Printnest</h1><p>Gerçek Zamanlı AI Portal</p>", unsafe_allow_html=True)
    with col2:
        with st.container(border=True):
            e = st.text_input("E-posta", key="login_email")
            p = st.text_input("Şifre", type="password", key="login_pass")
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                uid = verify_password(e, p)
                if uid:
                    st.session_state.user = {"email": e, "uid": uid}; st.rerun()
    st.stop()

# --- 7. MODEL VE SİDEBAR ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-2.5-flash")

with st.sidebar:
    st.markdown("### 💼 Printnest AI")
    if st.button("➕ Yeni Sohbet", use_container_width=True, type="primary"):
        st.session_state.current_thread_id = str(uuid.uuid4()); st.session_state.chat_session = None; st.rerun()
    st.divider()
    for t in get_user_threads(st.session_state.user["uid"]):
        if st.button(f"💬 {t['title']}", key=t['id'], use_container_width=True):
            st.session_state.current_thread_id = t['id']
            st.session_state.chat_session = model.start_chat(history=load_messages_from_thread(st.session_state.user["uid"], t['id']))
            st.rerun()

# --- 8. ANA CHAT EKRANI ---
if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

for msg in st.session_state.chat_session.history:
    with st.chat_message("assistant" if msg.role == "model" else "user"):
        st.markdown(msg.parts[0].text)

if prompt := st.chat_input("Hava durumu, borsa veya güncel haberleri sor..."):
    with st.chat_message("user"): st.markdown(prompt)
    save_message_to_db(st.session_state.user["uid"], st.session_state.current_thread_id, "user", prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("İnternette araştırılıyor..."):
            # 1. SERPER İLE CANLI VERİ ÇEK
            live_context = get_live_search(prompt)
            
            # 2. GEMINI İÇİN ÖZEL PROMPT HAZIRLA
            # Modelin bugünü bilmesi ve arama sonuçlarını kullanması için:
            enriched_prompt = f"""
            Bugünün Tarihi: {datetime.now().strftime('%d/%m/%Y')}
            İnternet Arama Sonuçları:
            {live_context}
            
            Soru: {prompt}
            
            Yukarıdaki güncel bilgileri kullanarak soruyu yanıtla. Eğer bilgiler yetersizse mevcut bilgini kullan ama önceliği arama sonuçlarına ver.
            """
            
            try:
                res = st.session_state.chat_session.send_message(enriched_prompt)
                st.markdown(res.text)
                save_message_to_db(st.session_state.user["uid"], st.session_state.current_thread_id, "model", res.text)
            except Exception as e:
                st.error(f"Hata: {e}")