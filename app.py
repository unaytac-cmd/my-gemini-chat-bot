# --- 3. GİRİŞ EKRANI (MODERN İKİYE BÖLÜNMÜŞ TASARIM) ---
if st.session_state.user is None:
    # Sayfayı iki sütuna bölüyoruz: %50 Tanıtım, %50 Giriş Formu
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("""
            # 💼 Printnest.com
            ### Kurumsal Yapay Zeka Çözümleri
            
            Printnest AI, iş süreçlerinizi hızlandırmak ve verimliliğinizi artırmak için tasarlandı.
            
            **Neler Sunuyoruz?**
            * 🚀 **Hızlı Yanıtlar:** Gemini 2.5 Flash ile anlık analiz.
            * 📁 **Sohbet Geçmişi:** Hiçbir fikri kaybetmeyin, geçmişe kolayca dönün.
            * 🔒 **Güvenli Altyapı:** Verileriniz kurumsal standartlarda korunur.
            * 🤖 **Özel Modeller:** İşinize odaklı akıllı asistan deneyimi.
            
            ---
            *Daha fazla bilgi için [printnest.com](https://printnest.com) adresini ziyaret edebilirsiniz.*
        """)
        # İstersen buraya bir görsel de ekleyebilirsin
        # st.image("logo.png", width=200)

    with col2:
        st.container(border=True) # Formu bir kutu içine alalım
        st.subheader("Hoş Geldiniz")
        tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
        
        with tab1:
            email = st.text_input("Kurumsal E-posta", key="login_email")
            password = st.text_input("Şifre", type="password", key="login_pass")
            
            if st.button("Sisteme Giriş Yap", use_container_width=True, type="primary"):
                if email and password:
                    try:
                        user = auth.get_user_by_email(email)
                        st.session_state.user = {"email": email, "uid": user.uid}
                        time.sleep(0.3)
                        st.rerun() 
                    except:
                        st.error("Giriş başarısız. Lütfen bilgilerinizi kontrol edin.")
                else:
                    st.warning("E-posta ve şifre zorunludur.")
                    
        with tab2:
            new_email = st.text_input("Yeni E-posta", key="signup_email")
            new_pass = st.text_input("Yeni Şifre", type="password", key="signup_pass")
            if st.button("Hesap Oluştur", use_container_width=True):
                if len(new_pass) >= 6:
                    try:
                        auth.create_user(email=new_email, password=new_pass)
                        st.success("Hesabınız oluşturuldu! Şimdi giriş yapabilirsiniz.")
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Şifre en az 6 karakter olmalıdır.")
    st.stop()