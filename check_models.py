import google.generativeai as genai
import os
from dotenv import load_dotenv

print("--- Gemini API Modeli Erişilebilirlik Kontrolü ---")

# --- API Anahtarını Yükleme ---
# Yerel .env dosyasından anahtarı almaya çalışın
try:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("Hata: GOOGLE_API_KEY ortam değişkeni bulunamadı.")
        print("Lütfen proje kök dizininizdeki '.env' dosyasına 'GOOGLE_API_KEY=\"SİZİN_ANAHTARINIZ\"' şeklinde anahtarınızı ekleyin.")
        exit() # Anahtar yoksa programdan çık

    genai.configure(api_key=api_key)
    print("API Anahtarı başarıyla yapılandırıldı.")

except Exception as e:
    print(f"Hata: API anahtarı yapılandırma hatası: {e}")
    exit() # Yapılandırma hatası olursa programdan çık

# --- Mevcut Modelleri Listeleme ---
print("\nAPI Anahtarınızla Erişilebilir Modeller:")
try:
    models_found = False
    for m in genai.list_models():
        # generateContent metodu destekleyen modelleri filtreleyelim
        if "generateContent" in m.supported_generation_methods:
            print(f"- Model Adı: {m.name}")
            print(f"  Desteklenen Metotlar: {m.supported_generation_methods}")
            models_found = True

    if not models_found:
        print("API anahtarınızla 'generateContent' destekleyen hiçbir model bulunamadı.")
        print("Bu durum bölgesel kısıtlamalardan veya API anahtarınızla ilgili bir sorundan kaynaklanıyor olabilir.")

except Exception as list_error:
    print(f"Hata: Modeller listelenirken bir hata oluştu: {list_error}")
    print("Lütfen internet bağlantınızı ve API anahtarınızın geçerliliğini kontrol edin.")

print("\n--- Kontrol Tamamlandı ---")