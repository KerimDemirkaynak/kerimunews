import os
import json
from atproto import Client

def main():
    BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
    BLUESKY_PASSWORD = os.environ.get("BLUESKY_PASSWORD")
    SITE_URL = "https://kerimunews.com" # Asıl domaininize göre güncelleyin

    if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
        print("Hata: Bluesky kimlik bilgileri bulunamadı (Secret'lar eksik)!")
        return

    # liste.json dosyasını doğrudan oku
    try:
        with open("liste.json", "r", encoding="utf-8") as f:
            haberler = json.load(f)
            
        if not haberler:
            print("Hata: liste.json boş.")
            return

        # En yeni haber listenin başında (0. indeks)
        yeni_haber = haberler[0]
        
    except Exception as e:
        print(f"Dosya okunurken hata oluştu: {e}")
        return

    title = yeni_haber.get("baslik") or yeni_haber.get("title")
    news_id = yeni_haber.get("id")

    if not title or not news_id:
        print("Hata: Haber içeriğinde 'baslik' veya 'id' bulunamadı.")
        return

    # Aynı haberi tekrar paylaşmamak için son paylaşılan ID'yi kontrol et
    # Eğer GitHub Actions'da çalışıyorsa ve repo geçmişi tutulmuyorsa 
    # bu dosya her seferinde sıfırlanabilir ancak manuel tetiklemelerde hayat kurtarır.
    last_posted_file = "last_posted_id.txt"
    if os.path.exists(last_posted_file):
        with open(last_posted_file, "r", encoding="utf-8") as f:
            last_posted_id = f.read().strip()
        
        if last_posted_id == str(news_id):
            print(f"Bu haber zaten paylaşıldı (ID: {news_id}). İşlem iptal ediliyor.")
            return

    # Paylaşılacak metni hazırla
    news_url = f"{SITE_URL}/haber.html?id={news_id}"
    post_text = f"🚨 Yeni Haber:\n\n{title}\n\nDetaylar: {news_url}"
    
    # Karakter sınırı kontrolü (Bluesky maksimum 300 karakter destekler)
    if len(post_text) > 300:
        kalan_bosluk = 300 - len(f"🚨 Yeni Haber:\n\n...\n\nDetaylar: {news_url}")
        post_text = f"🚨 Yeni Haber:\n\n{title[:kalan_bosluk]}...\n\nDetaylar: {news_url}"

    # Bluesky'da Paylaş
    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        print("Bluesky bağlantısı kuruldu, gönderi paylaşılıyor...")
        
        client.send_post(text=post_text)
        print(f"Gönderi başarıyla paylaşıldı: {title}")
        
        # Gönderi paylaşıldıysa ID'sini kaydet
        with open(last_posted_file, "w", encoding="utf-8") as f:
            f.write(str(news_id))
            
    except Exception as e:
        print(f"Bluesky'da paylaşılırken hata oluştu: {e}")

if __name__ == "__main__":
    main()
