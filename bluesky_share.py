import os
import json
import urllib.request
import time
from atproto import Client, client_utils

def main():
    BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
    BLUESKY_PASSWORD = os.environ.get("BLUESKY_PASSWORD")
    # 1. DÜZELTME: Doğru alan adı eklendi
    SITE_URL = "https://kerimdemirkaynak.github.io/kerimunews"

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
            
    except Exception as e:
        print(f"Dosya okunurken hata oluştu: {e}")
        return

    # Son paylaşılan haberin ID'sini oku
    last_posted_file = "last_posted_id.txt"
    last_posted_id = None
    if os.path.exists(last_posted_file):
        with open(last_posted_file, "r", encoding="utf-8") as f:
            last_posted_id = f.read().strip()

    # 2. DÜZELTME: Sadece 1 tane değil, son paylaşılandan bu yana eklenen tüm haberleri bul
    yeni_haberler = []
    for haber in haberler:
        news_id = haber.get("id")
        if str(news_id) == last_posted_id:
            break # Son paylaştığımız habere ulaştık, gerisi eski haber. Döngüyü bitir.
        yeni_haberler.append(haber)

    if not yeni_haberler:
        print("Yeni haber bulunamadı. İşlem iptal ediliyor.")
        return

    # ÖNLEM: Eğer script ilk kez çalışıyorsa geçmişteki yüzlerce haberi birden paylaşıp 
    # hesabı spam'a düşürmemesi için sadece en son 3 haberi paylaşsın.
    if not last_posted_id:
        print("İlk çalışma algılandı, flood olmaması için son 3 haber paylaşılacak...")
        yeni_haberler = yeni_haberler[:3]

    # Haberleri eskiden yeniye doğru sıralayalım ki, Bluesky'da kronolojik bir sırayla görünsün
    yeni_haberler.reverse()

    # Bluesky'a bağlan
    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        print("Bluesky bağlantısı kuruldu, paylaşımlar başlatılıyor...")
    except Exception as e:
        print(f"Bluesky'a giriş yapılamadı: {e}")
        return

    # Yeni haberleri sırayla paylaş
    for haber in yeni_haberler:
        title = haber.get("baslik") or haber.get("title")
        news_id = haber.get("id")
        image_url = haber.get("resim") or haber.get("image") or haber.get("gorsel")
        
        if not title or not news_id:
            continue

        news_url = f"{SITE_URL}/haber.html?id={news_id}"

        # Metin ve Link kartını hazırla
        tb = client_utils.TextBuilder()
        tb.text("🚨 Yeni Haber:\n\n")
        
        if len(title) > 200:
            tb.text(f"{title[:197]}...\n\n")
        else:
            tb.text(f"{title}\n\n")
            
        tb.link("🔗 Haberi Okumak İçin Tıklayın", news_url)

        # Gönderiyi Paylaş
        try:
            if image_url:
                # İnternetteki bir URL mi, yoksa bilgisayardaki bir dosya mı kontrolü
                if image_url.startswith("http"):
                    req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        img_data = response.read()
                else:
                    with open(image_url, "rb") as f:
                        img_data = f.read()
                
                client.send_image(text=tb, image=img_data, image_alt=title)
            else:
                client.send_post(text=tb)

            print(f"Başarıyla paylaşıldı: {title}")
            
            # Her başarılı paylaşımdan sonra ID'yi kaydet (Eğer ortada hata verirse kaldığı yerden devam edebilsin diye)
            with open(last_posted_file, "w", encoding="utf-8") as f:
                f.write(str(news_id))
                
            # Arka arkaya hızlı paylaşım yapıp Bluesky limitlerine takılmamak için 2 saniye bekle
            time.sleep(2)
            
        except Exception as e:
            print(f"Gönderi paylaşılırken hata oluştu (ID: {news_id}): {e}")

if __name__ == "__main__":
    main()
