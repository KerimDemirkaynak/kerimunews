import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import json
import time

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

def icerik_ve_resim_cek(entry):
    sonuc = {"metin": "", "resim": ""}
    
    # 1. ADIM: RSS İÇERİĞİNİ KONTROL ET (Anitrendz İçin En İyisi)
    ham_html = ""
    # feedparser 'content:encoded' etiketini 'content' olarak okur
    if 'content' in entry:
        ham_html = entry.content[0].value
    elif 'summary' in entry:
        ham_html = entry.summary
        
    if ham_html:
        soup_rss = BeautifulSoup(ham_html, 'html.parser')
        
        # Resim bul (RSS içindeki ilk resmi çeker)
        img_tag = soup_rss.find('img')
        if img_tag and img_tag.get('src'):
            sonuc["resim"] = img_tag['src']
            
        # Metin bul (RSS içindeki paragraflar)
        paragraflar = soup_rss.find_all('p')
        metin_parcalari = [p.get_text().strip() for p in paragraflar if len(p.get_text().strip()) > 30]
        if metin_parcalari:
            sonuc["metin"] = "\n\n".join(metin_parcalari)
            
    # 2. ADIM: EĞER RSS ÇOK KISAYSA (Özetse) VEYA RESİM YOKSA SİTEYE GİT (AWN için)
    # Metin 400 karakterden kısaysa bunun sadece özet olduğunu anlıyoruz
    if len(sonuc["metin"]) < 400 or not sonuc["resim"]:
        try:
            # Gerçek bir tarayıcı gibi davran (Bot engellerini aşmak için)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/'
            }
            response = requests.get(entry.link, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup_web = BeautifulSoup(response.content, 'html.parser')
                
                # Siteden kapak resmi bulma
                if not sonuc["resim"]:
                    og_image = soup_web.find("meta", property="og:image")
                    if og_image and og_image.get("content"):
                        sonuc["resim"] = og_image["content"]
                        
                # Siteden tam metin bulma
                if len(sonuc["metin"]) < 400:
                    # AWN ve ANN gibi sitelerin makale alanını daha geniş tarıyoruz
                    kapsayici = soup_web.find('article') or soup_web.find('div', class_='field-item') or soup_web
                    web_paragraflar = kapsayici.find_all('p')
                    web_metin = [p.get_text().strip() for p in web_paragraflar if len(p.get_text().strip()) > 30]
                    
                    if web_metin:
                        sonuc["metin"] = "\n\n".join(web_metin)
        except Exception as e:
            print(f"Web'den veri çekme hatası ({entry.link}): {e}")
            
    # Hala metin bulamadıysak varsayılan uyarı
    if len(sonuc["metin"]) < 50:
         sonuc["metin"] = "Tam metin çekilemedi. Lütfen orijinal kaynağa gidiniz."
         
    return sonuc

def tarih_formatla(entry):
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            t = entry.published_parsed
            gun = str(t.tm_mday)
            ay_ing = time.strftime("%b", t)
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
            
            # Akıllı İçerik Çekiciyi Kullan
            detaylar = icerik_ve_resim_cek(entry)
            
            # Çeviriler
            tr_baslik = cevir(orijinal_baslik)
            tr_ozet = cevir(orijinal_ozet[:300]) + "..."
            tr_tam_metin = cevir(detaylar["metin"])
            tr_tarih = tarih_formatla(entry)

            haber = {
                "id": haber_id,
                "kategori": kaynak["kategori"],
                "baslik": tr_baslik,
                "ozet": tr_ozet,
                "tamMetin": tr_tam_metin,
                "resim": detaylar["resim"],
                "kaynak": kaynak["isim"],
                "tarih": tr_tarih,
                "link": entry.link
            }
            
            tum_haberler.append(haber)
            haber_id += 1

    with open('haberler.json', 'w', encoding='utf-8') as f:
        json.dump(tum_haberler, f, ensure_ascii=False, indent=4)
    print("Haberler başarıyla kaydedildi!")

if __name__ == "__main__":
    ana_islem()
