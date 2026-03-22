import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import json
import time

# İngilizce ayları Türkçeye çevirmek için sözlük
AYLAR_TR = {
    "Jan": "Ocak", "Feb": "Şubat", "Mar": "Mart", "Apr": "Nisan", "May": "Mayıs", "Jun": "Haziran",
    "Jul": "Temmuz", "Aug": "Ağustos", "Sep": "Eylül", "Oct": "Ekim", "Nov": "Kasım", "Dec": "Aralık"
}

KAYNAKLAR = [
    {"url": "https://anitrendz.net/news/feed/", "kategori": "Anime", "isim": "Anitrendz"},
    {"url": "https://animehunch.com/feed/", "kategori": "Anime", "isim": "AnimeHunch"},
    {"url": "https://www.animenewsnetwork.com/all/rss.xml", "kategori": "Anime", "isim": "AnimeNewsNetwork"},
    {"url": "https://www.awn.com/news/rss.xml", "kategori": "Çizgi Film", "isim": "AWN"},
    {"url": "https://www.cartoonbrew.com/feed", "kategori": "Çizgi Film", "isim": "CartoonBrew"}
]

def cevir(metin):
    if not metin or metin.isspace():
        return ""
    try:
        translator = GoogleTranslator(source='auto', target='tr')
        return translator.translate(metin[:4999])
    except Exception as e:
        print(f"Çeviri hatası: {e}")
        return metin

def icerik_ve_resim_cek(url):
    # Hem resmi hem tam metni tek seferde döndürecek sözlük
    sonuc = {"metin": "Tam metin çekilemedi.", "resim": ""}
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. KAPAK RESMİNİ BULMA (Genellikle siteler og:image kullanır)
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            sonuc["resim"] = og_image["content"]

        # 2. TAM METNİ BULMA (Anitrendz ve diğerleri için ana kapsayıcıyı arıyoruz)
        icerik_alani = soup.find('div', class_='entry-content') or \
                       soup.find('div', class_='td-post-content') or \
                       soup.find('article') or \
                       soup

        paragraflar = icerik_alani.find_all('p')
        metin_parcalari = [p.get_text().strip() for p in paragraflar if len(p.get_text().strip()) > 30]
        
        if metin_parcalari:
            sonuc["metin"] = "\n\n".join(metin_parcalari)
            
    except Exception as e:
        print(f"Web'den veri çekme hatası ({url}): {e}")
        
    return sonuc

def tarih_formatla(entry):
    # RSS'deki yayınlanma tarihini alıp Türkçeye çevirir
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            t = entry.published_parsed
            gun = str(t.tm_mday)
            ay_ing = time.strftime("%b", t) # Mar, Apr vs.
            ay_tr = AYLAR_TR.get(ay_ing, ay_ing)
            yil = str(t.tm_year)
            return f"{gun} {ay_tr} {yil}"
    except Exception:
        pass
    return "Yakın Zamanda"

def ana_islem():
    tum_haberler = []
    haber_id = 1

    for kaynak in KAYNAKLAR:
        print(f"İşleniyor: {kaynak['isim']}...")
        feed = feedparser.parse(kaynak["url"])
        
        for entry in feed.entries[:3]:
            print(f" - Haber çekiliyor: {entry.title}")
            
            orijinal_baslik = entry.title
            orijinal_ozet = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text()
            link = entry.link
            
            # Siteye gidip resim ve tam metni al
            detaylar = icerik_ve_resim_cek(link)
            
            # Eğer siteden resim bulamadıysa, RSS summary içindeki resme bak (AnimeNewsNetwork vb. için)
            resim_url = detaylar["resim"]
            if not resim_url:
                soup_summary = BeautifulSoup(entry.get('summary', ''), 'html.parser')
                img_tag = soup_summary.find('img')
                if img_tag:
                    resim_url = img_tag.get('src', '')
            
            # Çeviriler
            tr_baslik = cevir(orijinal_baslik)
            tr_ozet = cevir(orijinal_ozet[:400]) + "..."
            tr_tam_metin = cevir(detaylar["metin"])
            tr_tarih = tarih_formatla(entry)

            haber = {
                "id": haber_id,
                "kategori": kaynak["kategori"],
                "baslik": tr_baslik,
                "ozet": tr_ozet,
                "tamMetin": tr_tam_metin,
                "resim": resim_url, # Yeni resim verimiz
                "kaynak": kaynak["isim"],
                "tarih": tr_tarih, # Türkçe tarih
                "link": link
            }
            
            tum_haberler.append(haber)
            haber_id += 1

    with open('haberler.json', 'w', encoding='utf-8') as f:
        json.dump(tum_haberler, f, ensure_ascii=False, indent=4)
    print("Haberler başarıyla kaydedildi!")

if __name__ == "__main__":
    ana_islem()
