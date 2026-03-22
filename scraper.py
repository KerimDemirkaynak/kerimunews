import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import json
import time
import os
import hashlib
from xml.sax.saxutils import escape

AYLAR_TR = {
    "Jan": "Ocak", "Feb": "Şubat", "Mar": "Mart", "Apr": "Nisan", "May": "Mayıs", "Jun": "Haziran",
    "Jul": "Temmuz", "Aug": "Ağustos", "Sep": "Eylül", "Oct": "Ekim", "Nov": "Kasım", "Dec": "Aralık"
}

KAYNAKLAR = [
    {"url": "https://anitrendz.net/news/feed/", "kategori": "Anime", "isim": "Anitrendz"},
    {"url": "https://animehunch.com/feed/", "kategori": "Anime", "isim": "AnimeHunch"},
    {"url": "https://www.animenewsnetwork.com/all/rss.xml", "kategori": "Anime", "isim": "AnimeNewsNetwork"},
    {"url": "https://www.cbr.com/feed/category/anime/", "kategori": "Anime", "isim": "CBR Anime"},
    {"url": "https://www.cbr.com/feed/tag/cartoons/", "kategori": "Çizgi Film", "isim": "CBR Çizgi Film"},
    {"url": "https://www.cartoonbrew.com/feed", "kategori": "Çizgi Film", "isim": "CartoonBrew"}
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.google.com/'
}

def id_olustur(link):
    return hashlib.md5(link.encode('utf-8')).hexdigest()[:10]

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
    ham_html = ""
    if 'content' in entry:
        ham_html = entry.content[0].value
    elif 'summary' in entry:
        ham_html = entry.summary
        
    if ham_html:
        soup_rss = BeautifulSoup(ham_html, 'html.parser')
        img_tag = soup_rss.find('img')
        if img_tag and img_tag.get('src'):
            sonuc["resim"] = img_tag['src']
            
        paragraflar = soup_rss.find_all('p')
        metin_parcalari = [p.get_text().strip() for p in paragraflar if len(p.get_text().strip()) > 30]
        if metin_parcalari:
            sonuc["metin"] = "\n\n".join(metin_parcalari)
            
    if len(sonuc["metin"]) < 400 or not sonuc["resim"]:
        try:
            response = requests.get(entry.link, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                soup_web = BeautifulSoup(response.content, 'html.parser')
                if not sonuc["resim"]:
                    og_image = soup_web.find("meta", property="og:image")
                    if og_image and og_image.get("content"):
                        sonuc["resim"] = og_image["content"]
                if len(sonuc["metin"]) < 400:
                    kapsayici = soup_web.find('article') or soup_web.find('div', class_='field-item') or soup_web
                    web_paragraflar = kapsayici.find_all('p')
                    web_metin = [p.get_text().strip() for p in web_paragraflar if len(p.get_text().strip()) > 30]
                    if web_metin:
                        sonuc["metin"] = "\n\n".join(web_metin)
        except Exception:
            pass
            
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
    return time.strftime("%d %B %Y")

def rss_olustur(liste):
    rss_items = ""
    for h in liste[:20]: # RSS içine sadece en yeni 20 haberi koyalım
        rss_items += f"""
        <item>
            <title>{escape(h['baslik'])}</title>
            <link>{escape(h['link'])}</link>
            <description>{escape(h['ozet'])}</description>
            <category>{escape(h['kategori'])}</category>
            <source url="{escape(h['link'])}">{escape(h['kaynak'])}</source>
            <pubDate>{escape(h['tarih'])}</pubDate>
        </item>"""

    rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>Kerimu Animasyon Haberleri</title>
    <link>https://kerimdemirkaynak.github.io</link>
    <description>Otomatik Türkçe çevirili global anime ve çizgi film haberleri.</description>
    <language>tr-TR</language>
    {rss_items}
</channel>
</rss>"""

    with open('rss.xml', 'w', encoding='utf-8') as f:
        f.write(rss_feed)

def ana_islem():
    # Klasör yoksa oluştur
    if not os.path.exists('haberler'):
        os.makedirs('haberler')

    eski_liste = []
    # 1. Ana Kataloğu (liste.json) Oku
    if os.path.exists('liste.json'):
        try:
            with open('liste.json', 'r', encoding='utf-8') as f:
                eski_liste = json.load(f)
        except Exception:
            print("Eski liste.json okunamadı, sıfırdan başlanıyor.")
            
    mevcut_id_listesi = {h['id'] for h in eski_liste}
    yeni_eklenenler = []

    for kaynak in KAYNAKLAR:
        print(f"\nİşleniyor: {kaynak['isim']}...")
        try:
            response = requests.get(kaynak["url"], headers=HEADERS, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:3]:
                link = entry.link
                haber_id = id_olustur(link)
                
                # Eğer haber zaten kataloğumuzda varsa atla
                if haber_id in mevcut_id_listesi:
                    print(f" - Zaten arşivde var, atlanıyor: {entry.title}")
                    continue
                
                print(f" + YENİ Haber Çekiliyor: {entry.title}")
                orijinal_baslik = entry.title
                orijinal_ozet = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text()
                
                detaylar = icerik_ve_resim_cek(entry)
                
                tr_baslik = cevir(orijinal_baslik)
                tr_ozet = cevir(orijinal_ozet[:250]) + "..."
                tr_tam_metin = cevir(detaylar["metin"])
                tr_tarih = tarih_formatla(entry)

                # Ana Katalog İçin Hafif Veri (tamMetin YOK)
                katalog_verisi = {
                    "id": haber_id,
                    "kategori": kaynak["kategori"],
                    "baslik": tr_baslik,
                    "ozet": tr_ozet,
                    "resim": detaylar["resim"],
                    "kaynak": kaynak["isim"],
                    "tarih": tr_tarih,
                    "link": link
                }
                yeni_eklenenler.append(katalog_verisi)

                # Özel Haber Dosyası İçin Tam Veri (Tam Metin VAR)
                tam_veri = katalog_verisi.copy()
                tam_veri["tamMetin"] = tr_tam_metin

                # Haberi kendi klasörüne ID'si ile kaydet
                with open(f'haberler/{haber_id}.json', 'w', encoding='utf-8') as f:
                    json.dump(tam_veri, f, ensure_ascii=False, indent=4)
                
        except Exception as e:
            print(f"HATA - {kaynak['isim']} atlanıyor: {e}")
            continue 

    # 3. Yeni haberleri kataloğun en başına ekle
    guncel_liste = yeni_eklenenler + eski_liste

    if guncel_liste:
        with open('liste.json', 'w', encoding='utf-8') as f:
            json.dump(guncel_liste, f, ensure_ascii=False, indent=4)
            
        rss_olustur(guncel_liste)
        print(f"\nİşlem tamam! {len(yeni_eklenenler)} yeni haber eklendi. Arşivdeki toplam haber: {len(guncel_liste)}")
    else:
        print("Hiçbir kaynaktan haber çekilemedi!")

if __name__ == "__main__":
    ana_islem()
