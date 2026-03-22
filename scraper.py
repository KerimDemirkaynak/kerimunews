import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import json
import os
from datetime import datetime

# RSS Kaynaklarımız ve Kategorileri
KAYNAKLAR = [
    {"url": "https://anitrendz.net/news/feed/", "kategori": "Anime", "isim": "Anitrendz"},
    {"url": "https://animehunch.com/feed/", "kategori": "Anime", "isim": "AnimeHunch"},
    {"url": "https://www.animenewsnetwork.com/all/rss.xml", "kategori": "Anime", "isim": "AnimeNewsNetwork"},
    {"url": "https://www.awn.com/news/rss.xml", "kategori": "Çizgi Film", "isim": "AWN"},
    {"url": "https://www.cartoonbrew.com/feed", "kategori": "Çizgi Film", "isim": "CartoonBrew"}
]

# Çeviri fonksiyonu (Google Translate kullanır, API key gerektirmez)
def cevir(metin):
    if not metin or metin.isspace():
        return ""
    try:
        # Metin çok uzunsa parça parça çevirmek gerekebilir, ancak şimdilik tek parça deniyoruz
        translator = GoogleTranslator(source='auto', target='tr')
        return translator.translate(metin[:4999]) # Google Translate 5000 karakter sınırı
    except Exception as e:
        print(f"Çeviri hatası: {e}")
        return metin # Hata olursa orijinalini döndür

# Tam metni web sitesinden kazıyan fonksiyon
def tam_metni_cek(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Çoğu haber sitesinde asıl metin <p> etiketleri içindedir.
        # Daha spesifik siteler için (örn: ANN) buraya özel class seçiciler eklenebilir.
        paragraflar = soup.find_all('p')
        metin_parcalari = [p.get_text().strip() for p in paragraflar if len(p.get_text().strip()) > 20]
        
        tam_metin = "\n\n".join(metin_parcalari)
        return tam_metin if tam_metin else "Tam metin çekilemedi."
    except Exception as e:
        print(f"Metin çekme hatası ({url}): {e}")
        return "Tam metin çekilemedi."

def ana_islem():
    tum_haberler = []
    haber_id = 1

    for kaynak in KAYNAKLAR:
        print(f"İşleniyor: {kaynak['isim']}...")
        feed = feedparser.parse(kaynak["url"])
        
        # Her kaynaktan en yeni 3 haberi alalım (GitHub Actions süresini aşmamak için)
        for entry in feed.entries[:3]:
            print(f" - Haber çekiliyor: {entry.title}")
            
            # Orijinal veriler
            orijinal_baslik = entry.title
            orijinal_ozet = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text()
            link = entry.link
            
            # Tam metni çek
            orijinal_tam_metin = tam_metni_cek(link)
            
            # Çeviriler (Bu kısım biraz zaman alabilir)
            tr_baslik = cevir(orijinal_baslik)
            tr_ozet = cevir(orijinal_ozet[:500]) + "..." # Özeti kısa tutalım
            tr_tam_metin = cevir(orijinal_tam_metin)

            haber = {
                "id": haber_id,
                "kategori": kaynak["kategori"],
                "baslik": tr_baslik,
                "ozet": tr_ozet,
                "tamMetin": tr_tam_metin,
                "kaynak": kaynak["isim"],
                "tarih": datetime.now().strftime("%d %B %Y"),
                "link": link
            }
            
            tum_haberler.append(haber)
            haber_id += 1

    # JSON dosyasına kaydet
    with open('haberler.json', 'w', encoding='utf-8') as f:
        json.dump(tum_haberler, f, ensure_ascii=False, indent=4)
    print("Haberler başarıyla haberler.json dosyasına kaydedildi!")

if __name__ == "__main__":
    ana_islem()
