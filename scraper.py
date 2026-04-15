import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from google import genai
import json
import time
import os
import hashlib
from xml.sax.saxutils import escape
import warnings

# BeautifulSoup'un gereksiz uyarılarını gizler
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# --- YENİ GEMINI API YAPILANDIRMASI ---
API_KEY = os.environ.get("GEMINI_API_KEY")
if API_KEY:
    client = genai.Client(api_key=API_KEY)
    model_name = 'gemini-2.5-flash'
else:
    client = None

AYLAR_TR = {
    "Jan": "Ocak", "Feb": "Şubat", "Mar": "Mart", "Apr": "Nisan", "May": "Mayıs", "Jun": "Haziran",
    "Jul": "Temmuz", "Aug": "Ağustos", "Sep": "Eylül", "Oct": "Ekim", "Nov": "Kasım", "Dec": "Aralık"
}

# YENİ KAYNAK EKLENDİ (Animation Magazine)
KAYNAKLAR = [
    {"url": "https://anitrendz.net/news/feed/", "kategori": "Anime", "isim": "Anitrendz"},
    {"url": "https://animehunch.com/feed/", "kategori": "Anime", "isim": "AnimeHunch"},
    {"url": "https://www.animenewsnetwork.com/all/rss.xml", "kategori": "Anime", "isim": "AnimeNewsNetwork"},
    {"url": "https://www.cbr.com/feed/category/anime/", "kategori": "Anime", "isim": "CBR Anime"},
    {"url": "https://www.cbr.com/feed/tag/cartoons/", "kategori": "Çizgi Film", "isim": "CBR Çizgi Film"},
    {"url": "https://www.cartoonbrew.com/feed", "kategori": "Çizgi Film", "isim": "CartoonBrew"},
    {"url": "https://www.animationmagazine.net/category/tv/feed/", "kategori": "Çizgi Film", "isim": "AnimationMagazine"}
]

# BOT KORUMASI AŞMAK İÇİN GELİŞMİŞ HEADERS
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1'
}

def id_olustur(link):
    return hashlib.md5(link.encode('utf-8')).hexdigest()[:10]

def cevir(metin):
    if not metin or metin.isspace():
        return ""
    
    if client:
        prompt = f"""
Sen profesyonel bir anime ve animasyon haberleri çevirmenisin.
Aşağıdaki İngilizce metni Türkçe'ye çevir.

KESİN KURALLAR:
1. Karakter isimleri, anime/manga isimleri ve stüdyo isimlerini KESİNLİKLE orijinal İngilizce veya Romaji haliyle bırak.
2. Anime isimlerinin yanında veya içinde geçen İngilizce meslek/unvanları KESİNLİKLE Türkçeye çevir (Örn: "character designer" -> "karakter tasarımcısı", "director" -> "yönetmen", "series composer" -> "seri senaristi/kurgucusu").
3. Haber metni resmi ama anime fanlarına hitap eden, samimi ve heyecanlı bir tonda olmalı.
4. Abartılı emoji veya argo kelimeler KULLANMA.
5. Orijinal haberin tonunu koru.
6. Metne hiçbir bilgi ekleme veya çıkarma.
7. Türkçe mükemmel, akıcı ve doğal olacak.
8. Cümleler çok uzun ve karmaşıksa, anlamı bozmadan kır/böl.
9. Gereksiz tekrarları temizle.
10. SADECE çevrilmiş Türkçe metni ver, "İşte çeviri:" gibi ek açıklamalar yapma.

Çevrilecek Metin:
{metin[:4999]}
"""
        for deneme in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"Gemini API hatası (Deneme {deneme+1}/3): {e}")
                time.sleep(5) 
        
        print("Gemini API 3 kez başarısız oldu, Yedek Çeviriye geçiliyor...")

    try:
        translator = GoogleTranslator(source='auto', target='tr')
        return translator.translate(metin[:4999])
    except Exception as e:
        print(f"Yedek Çeviri hatası: {e}")
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
            
        metin_parcalari = []
        for element in soup_rss.find_all(['p', 'ul']):
            if element.name == 'p':
                text = element.get_text().strip()
                if len(text) > 30:
                    metin_parcalari.append(text)
            elif element.name == 'ul':
                for li in element.find_all('li'):
                    text = li.get_text().strip()
                    if len(text) > 5:
                        metin_parcalari.append("- " + text)
                        
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
                    
                    web_metin_parcalari = []
                    for element in kapsayici.find_all(['p', 'ul']):
                        if element.name == 'p':
                            text = element.get_text().strip()
                            if len(text) > 30:
                                web_metin_parcalari.append(text)
                        elif element.name == 'ul':
                            for li in element.find_all('li'):
                                text = li.get_text().strip()
                                if len(text) > 5:
                                    web_metin_parcalari.append("- " + text)
                                    
                    if web_metin_parcalari:
                        sonuc["metin"] = "\n\n".join(web_metin_parcalari)
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
    for h in liste[:20]:
        kendi_linkimiz = f"https://kerimdemirkaynak.github.io/kerimunews/haber.html?id={h['id']}"
        resim_url = h.get('resim', '')
        enclosure_tag = f'<enclosure url="{escape(resim_url)}" type="image/jpeg" length="0" />' if resim_url else ""
        
        rss_items += f"""
        <item>
            <title>{escape(h['baslik'])}</title>
            <link>{escape(kendi_linkimiz)}</link>
            <guid>{escape(kendi_linkimiz)}</guid>
            <description><![CDATA[<img src="{resim_url}" /><br><br>{h['ozet']}]]></description>
            <category>{escape(h['kategori'])}</category>
            <source url="{escape(h['link'])}">{escape(h['kaynak'])}</source>
            <pubDate>{escape(h['tarih'])}</pubDate>
            {enclosure_tag}
        </item>"""

    rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>Kerimu Animasyon Haberleri</title>
    <link>https://kerimdemirkaynak.github.io/kerimunews/</link>
    <description>Otomatik Türkçe çevirili global anime ve çizgi film haberleri.</description>
    <language>tr-TR</language>
    {rss_items}
</channel>
</rss>"""

    with open('rss.xml', 'w', encoding='utf-8') as f:
        f.write(rss_feed)

def ana_islem():
    if not os.path.exists('haberler'):
        os.makedirs('haberler')

    eski_liste = []
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
                
                if haber_id in mevcut_id_listesi:
                    print(f" - Zaten arşivde var, atlanıyor: {entry.title}")
                    continue
                
                print(f" + YENİ Haber Çekiliyor ve Çevriliyor: {entry.title}")
                orijinal_baslik = entry.title
                orijinal_ozet = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text()
                
                detaylar = icerik_ve_resim_cek(entry)
                
                tr_baslik = cevir(orijinal_baslik)
                tr_ozet = cevir(orijinal_ozet[:250]) + "..."
                tr_tam_metin = cevir(detaylar["metin"])
                tr_tarih = tarih_formatla(entry)

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

                tam_veri = katalog_verisi.copy()
                tam_veri["tamMetin"] = tr_tam_metin

                with open(f'haberler/{haber_id}.json', 'w', encoding='utf-8') as f:
                    json.dump(tam_veri, f, ensure_ascii=False, indent=4)
                
                # API limitlerini korumak için 3 saniye bekle
                time.sleep(3)
                
        except Exception as e:
            print(f"HATA - {kaynak['isim']} atlanıyor: {e}")
            continue 

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
