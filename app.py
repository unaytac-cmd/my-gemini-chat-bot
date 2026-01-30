import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
import uuid
from datetime import datetime
import requests
from googlesearch import search

# --- 1. FIREBASE (DEĞİŞMEDİ) ---
if not firebase_admin._apps:
    try:
        fb_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(fb_dict)
        firebase_admin.initialize_app(cred)
    except: st.stop()
db = firestore.client()

# --- 2. ŞİFRE DOĞRULAMA (DEĞİŞMEDİ) ---
def verify_password(email, password):
    try:
        api_key = st.secrets["FIREBASE_WEB_API_KEY"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        res = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
        return res.json()["localId"] if res.status_code == 200 else None
    except: return None

# --- 3. İNTERNET ARAMA MOTORU (GÜNCELLENDİ) ---
def get_live_context(query):
    """Google'dan en güncel 5 sonucu çeker."""
    try:
        results = []
        # stop=5 yaparak daha fazla veri çekiyoruz
        for url in search(query, stop=5, lang='tr'):
            results.append(url)
        if results:
            return "\n\nCRITICAL CURRENT DATA (Kullanmak Zorunlusun):\n" + "\n".join(results)
        return ""
    except Exception as e:
        return f"\n(Arama Hatası: {str(e)})"

# --- 4. TASARIM (STABİL) ---
st.set_page_config(page_title="Printnest AI", page_icon="💼", layout="wide")
st.markdown("<style>[data-testid='stAppViewBlockContainer'] { opacity: 1 !important; }</style>", unsafe_allow_html=True)

if "user" not in st.session_state: st.session_state.user = None
if "current_thread_id" not in st.session_state: st.session_state.current_thread_id = None

# --- 5. GİRİŞ & KAYIT (DEĞİŞMEDİ) ---
if st.session_state.user is None:
    # (Önceki giriş ekranı kodları buraya gelecek - sistemin iskeleti aynı)
    st.title("💼 Printnest Login")
    # ... (Login UI kodlarını buraya eklediğini varsayıyorum)
    st.stop()

# --- 6. MODEL KURULUMU (SERT TALİMAT EKLENDİ) ---
user_id = st.session_state.user["uid"]
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Modele "Güncel ol" emri veriyoruz
model = genai.GenerativeModel(
    model_name="models/gemini-2.0-flash",
    system_instruction="Sen Printnest AI asistanısın. Sana sunulan 'CRITICAL CURRENT DATA' içindeki linkler ve bilgiler senin eğitim verilerinden daha günceldir. Eğer kullanıcı borsa, haber veya anlık bir durum sorarsa, KENDİ HAFIZANI DEĞİL, bu güncel verileri kullanmak ZORUNDASIN. Veri bulamazsan bunu açıkça belirt."
)

# --- 7. CHAT MANTIĞI ---
if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

if prompt := st.chat_input("Mesajınızı yazın..."):
    st.chat_message("user").markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("İnternet verileri Gemini'ye aktarılıyor..."):
            # Arama yap ve prompt'u güçlendir
            live_info = get_live_context(prompt)
            # Eğer güncel veri bulunduysa Gemini'ye "Bu veriyi kullan" diyoruz
            final_prompt = f"Kullanıcı Sorusu: {prompt} \n\n{live_info}"
            
            try:
                response = st.session_state.chat_session.send_message(final_prompt)
                # Kullanıcıya temiz cevap göster (Sistem notlarını gizle)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Hata: {e}")