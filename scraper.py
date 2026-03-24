import feedparser
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import json
import time
import os
import hashlib
from xml.sax.saxutils import escape
from urllib.parse import urlparse

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

def cevir(metin, max_uzunluk=4500, tekrar_sayisi=3):
    if not metin or metin.isspace():
        return ""
    
    # Eğer metin sınırın altındaysa direkt çevir
    if len(metin) <= max_uzunluk:
        for deneme in range(tekrar_sayisi):
            try:
                translator = GoogleTranslator(source='auto', target='tr')
                return translator.translate(metin)
            except Exception as e:
                print(f"   [!] Çeviri hatası (Deneme {deneme+1}/{tekrar_sayisi}): {e}")
                time.sleep(2) # Hata alırsan 2 saniye bekle ve tekrar dene
        
        print("   [!] Çeviri tamamen başarısız oldu, orijinal metin kullanılıyor.")
        return metin

    # Eğer metin çok uzunsa bölerek çevir (Ewilan's Quest gibi makalelerin yarım kalmaması için)
    else:
        cevrilmis_parcalar = []
        parcalar = [metin[i:i+max_uzunluk] for i in range(0, len(metin), max_uzunluk)]
        
        for parca in parcalar:
            for deneme in range(tekrar_sayisi):
                try:
                    translator = GoogleTranslator(source='auto', target='tr')
                    cevrilmis_parca = translator.translate(parca)
                    cevrilmis_parcalar.append(cevrilmis_parca)
                    time.sleep(1) # API'yi yormamak için parçalar arası kısa bekleme
                    break 
                except Exception as e:
                     print(f"   [!] Parça çeviri hatası (Deneme {deneme+1}/{tekrar_sayisi}): {e}")
                     time.sleep(2)
            else:
                 cevrilmis_parcalar.append(parca)
                 
        return "".join(cevrilmis_parcalar)

def icerik_ve_resim_cek(entry):
    sonuc = {"metin": "", "resim": ""}
    ham_html = ""
    
    # 1. Aşama: RSS Feed İçinden Veri Çekmeyi Dene
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
        metin_parcalari = [p.get_text().strip() for p in paragraflar if len(p.get_text().strip()) > 10]
        if metin_parcalari:
            sonuc["metin"] = "\n\n".join(metin_parcalari)
            
    # 2. Aşama: Web Kazıma (Eğer içerik yetersizse ana siteye git)
    if len(sonuc["metin"]) < 400 or not sonuc["resim"]:
        try:
            response = requests.get(entry.link, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                soup_web = BeautifulSoup(response.content, 'html.parser')
                
                if not sonuc["resim"]:
                    og_image = soup_web.find("meta", property="og:image")
                    if og_image and og_image.get("content"):
                        sonuc["resim"] = og_image["content"]
                
                # Çeşitli sitelerin kapsayıcı formatları (AnimeNewsNetwork için KonaBody dahil)
                kapsayici = soup_web.find('div', class_='KonaBody') or soup_web.find('section', id='article-body') or soup_web.find('article') or soup_web.find('div', class_='field-item') or soup_web
                
                if kapsayici:
                    islenmis_icerik = []
                    
                    for eleman in kapsayici.find_all(['h2', 'h3', 'p', 'figure', 'ul', 'ol', 'blockquote']):
                        
                        # Çift çekilmeyi (duplikasyon) önleme
                        if eleman.name in ['p', 'h2', 'h3', 'ul', 'ol']:
                            if eleman.find_parent(['blockquote', 'ul', 'ol', 'figure']):
                                continue
                                
                        if eleman.name in ['h2', 'h3']:
                            baslik_metni = eleman.get_text().strip()
                            if baslik_metni:
                                islenmis_icerik.append(f"<h2>{cevir(baslik_metni)}</h2>")
                                
                        elif eleman.name == 'p':
                            # Gereksiz kodları temizle
                            for tag in eleman.find_all(['iframe', 'script', 'style', 'span']):
                                tag.decompose()
                            p_metin = eleman.get_text().strip()
                            if len(p_metin) > 10 and not p_metin.isspace():
                                islenmis_icerik.append(f"<p>{cevir(p_metin)}</p>")
                                
                        elif eleman.name in ['ul', 'ol']:
                            liste_icerigi = []
                            for li in eleman.find_all('li'):
                                for tag in li.find_all(['iframe', 'script', 'style', 'span']):
                                    tag.decompose()
                                li_metin = li.get_text().strip()
                                if len(li_metin) > 3:
                                    liste_icerigi.append(f"<li>{cevir(li_metin)}</li>")
                            if liste_icerigi:
                                liste_tipi = eleman.name
                                islenmis_icerik.append(f"<{liste_tipi}>\n" + "\n".join(liste_icerigi) + f"\n</{liste_tipi}>")
                                
                        elif eleman.name == 'blockquote':
                            for tag in eleman.find_all(['iframe', 'script', 'style']):
                                tag.decompose()
                            alinti_metni = eleman.get_text(separator=" ").strip()
                            if len(alinti_metni) > 10:
                                islenmis_icerik.append(f'<blockquote style="border-left: 4px solid #1DA1F2; padding-left: 15px; margin: 15px 0; font-style: italic; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">{cevir(alinti_metni)}</blockquote>')
                                
                        elif eleman.name == 'figure':
                            img = eleman.find('img')
                            if img:
                                src = img.get('data-img-url') or img.get('data-src') or img.get('src')
                                # Link root'tan başlıyorsa domain'i başına ekle
                                if src and src.startswith('/'):
                                    parsed_uri = urlparse(entry.link)
                                    ana_domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
                                    src = ana_domain + src
                                if src:
                                    islenmis_icerik.append(f'<br><img src="{src}" style="max-width:100%; height:auto; border-radius:8px; margin-bottom:15px;"/><br>')

                    if islenmis_icerik:
                        sonuc["metin"] = "\n".join(islenmis_icerik)
                        
        except Exception as e:
            print(f"İçerik çekme hatası ({entry.link}): {e}")
            
    if len(sonuc["metin"]) < 50:
         sonuc["metin"] = "<p>Tam metin çekilemedi. Lütfen orijinal kaynağa gidiniz.</p>"
         
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
                
                print(f" + YENİ Haber Çekiliyor: {entry.title}")
                orijinal_baslik = entry.title
                
                orijinal_ozet_html = entry.get('summary', '')
                orijinal_ozet = BeautifulSoup(orijinal_ozet_html, 'html.parser').get_text()
                
                detaylar = icerik_ve_resim_cek(entry)
                
                tr_baslik = cevir(orijinal_baslik)
                tr_ozet = cevir(orijinal_ozet[:250]) + "..."
                tr_tarih = tarih_formatla(entry)
                tr_tam_metin = detaylar["metin"]

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
