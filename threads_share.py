import os
import json
import requests
import time

TOKEN_FILE = "threads_token.txt"

def get_working_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            saved_token = f.read().strip()
            if saved_token:
                return saved_token
    return os.environ.get("THREADS_ACCESS_TOKEN")

def post_to_threads(access_token, user_id, title, url, source, image_url=None):
    full_text = f"{title}\n\nKaynak: {source}\n{url}"
    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    payload = {"text": full_text, "access_token": access_token}
    
    if image_url and image_url.startswith("http"):
        payload.update({"media_type": "IMAGE", "image_url": image_url})
    else:
        payload.update({"media_type": "TEXT"})
    
    create_res = requests.post(create_url, data=payload)
    if create_res.status_code != 200:
        print(f"❌ Oluşturma hatası: {create_res.text}")
        return False
        
    container_id = create_res.json().get('id')
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    pub_res = requests.post(publish_url, data={"creation_id": container_id, "access_token": access_token})
    
    if pub_res.status_code != 200:
        print(f"❌ Yayınlama hatası: {pub_res.text}")
        return False
    return True

def main():
    access_token = get_working_token()
    if not access_token:
        print("❌ Token yok!")
        return

    last_posted_file = "last_posted_threads.txt"   # <-- DOĞRU DOSYA
    last_posted_id = None

    # Dosyadan oku
    if os.path.exists(last_posted_file):
        with open(last_posted_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                last_posted_id = content
                print(f"📄 Dosyadaki ID: '{last_posted_id}'")
            else:
                print("⚠️ Dosya boş, ilk çalışma varsayılıyor.")
    else:
        print("⚠️ Dosya yok, ilk çalışma.")

    # JSON'u oku
    with open("liste.json", 'r', encoding='utf-8') as f:
        news_list = json.load(f)

    if not news_list:
        print("❌ liste.json boş.")
        return

    # En yeniler başta olacak şekilde sırala (liste muhtemelen eskiden yeniye)
    news_list.reverse()

    # Yeni haberleri topla
    yeni_haberler = []
    eslesme_bulundu = False

    for haber in news_list:
        haber_id = str(haber.get('id', ''))   # string'e çevir
        if haber_id == last_posted_id:
            eslesme_bulundu = True
            break   # eşleşen ID'ye geldik, daha eski haberleri alma
        yeni_haberler.append(haber)

    print(f"📊 Toplam haber: {len(news_list)}, Yeni haber: {len(yeni_haberler)}")

    # Eğer dosyadaki ID listede yoksa, hiç paylaşma ve en son ID'yi güncelle
    if last_posted_id is not None and not eslesme_bulundu:
        print("⚠️ Dosyadaki ID listede bulunamadı! Muhtemelen haber silinmiş veya ID formatı farklı.")
        print("👉 Hiç paylaşım yapılmadan, en son haberin ID'si dosyaya yazılacak.")
        if news_list:
            newest_id = str(news_list[0].get('id', ''))
            with open(last_posted_file, "w", encoding="utf-8") as f:
                f.write(newest_id)
            print(f"✅ Dosyaya yeni ID yazıldı: '{newest_id}'")
        return   # paylaşım yok

    if not yeni_haberler:
        print("✅ Yeni haber yok.")
        return

    # İlk çalışma – sadece son 3 haber
    if last_posted_id is None:
        print("🚀 İlk çalışma, son 3 haber paylaşılacak.")
        yeni_haberler = yeni_haberler[:3]

    # Paylaşım sırası (eskiden yeniye – isteğe bağlı)
    yeni_haberler.reverse()

    # User ID
    user_id = requests.get(f"https://graph.threads.net/v1.0/me?access_token={access_token}").json().get('id')
    if not user_id:
        print("❌ User ID alınamadı!")
        return

    for haber in yeni_haberler:
        news_id = str(haber.get('id', ''))
        title = haber.get('baslik', '')
        url = haber.get('link', '')
        source = haber.get('kaynak', 'Anitrendz')
        image_url = haber.get('resim', '')

        if post_to_threads(access_token, user_id, title, url, source, image_url):
            print(f"✅ Paylaşıldı: {title}")
            with open(last_posted_file, "w", encoding="utf-8") as f:
                f.write(news_id)
            time.sleep(15)
        else:
            print(f"❌ Başarısız: {title}")

if __name__ == "__main__":
    main()
