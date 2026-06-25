import os
import json
import requests
import time

TOKEN_FILE = "threads_token.txt"
LAST_POSTED_FILE = "last_posted_threads.txt"

def get_working_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token:
                return token
    return os.environ.get("THREADS_ACCESS_TOKEN")

def post_to_threads(access_token, user_id, title, url, source, image_url=None):
    full_text = f"{title}\n\nKaynak: {source}\n{url}"
    
    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    payload = {
        "text": full_text,
        "access_token": access_token,
        "media_type": "IMAGE" if image_url and image_url.startswith("http") else "TEXT"
    }
    
    if payload["media_type"] == "IMAGE":
        payload["image_url"] = image_url

    # Thread oluştur
    create_res = requests.post(create_url, data=payload)
    if create_res.status_code != 200:
        print(f"❌ Oluşturma hatası: {create_res.text}")
        return False

    container_id = create_res.json().get('id')
    if not container_id:
        print("❌ Container ID alınamadı")
        return False

    # Yayınla
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    pub_res = requests.post(publish_url, data={
        "creation_id": container_id,
        "access_token": access_token
    })

    if pub_res.status_code != 200:
        print(f"❌ Yayınlama hatası: {pub_res.text}")
        return False

    return True

def main():
    access_token = get_working_token()
    if not access_token:
        print("❌ Token bulunamadı!")
        return

    # Son paylaşılan ID'yi oku
    last_posted_id = None
    if os.path.exists(LAST_POSTED_FILE):
        with open(LAST_POSTED_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                last_posted_id = content
                print(f"📄 Son paylaşılan ID: {last_posted_id}")

    # JSON oku
    with open("liste.json", 'r', encoding='utf-8') as f:
        news_list = json.load(f)

    if not news_list:
        print("❌ liste.json boş.")
        return

    # JSON zaten en yeni → en eski şeklinde olduğu için reverse() YAPMIYORUZ
    yeni_haberler = []
    for haber in news_list:          # ← en yeniden başlıyoruz
        haber_id = str(haber.get('id', ''))
        
        if haber_id == last_posted_id:
            break  # Bu ve daha eskileri atla
        
        yeni_haberler.append(haber)

    print(f"📊 Toplam haber: {len(news_list)} | Paylaşılacak yeni haber: {len(yeni_haberler)}")

    if not yeni_haberler:
        print("✅ Yeni haber yok.")
        return

    # İlk çalıştırma için güvenlik (çok fazla paylaşım olmasın)
    if last_posted_id is None:
        print("🚀 İlk çalıştırma → sadece son 5 haber paylaşılacak.")
        yeni_haberler = yeni_haberler[:5]

    # User ID al
    me_res = requests.get(f"https://graph.threads.net/v1.0/me?access_token={access_token}")
    user_id = me_res.json().get('id')
    if not user_id:
        print("❌ User ID alınamadı!")
        return

    # Paylaşım
    for haber in yeni_haberler:   # en yeni başta
        news_id = str(haber.get('id', ''))
        title = haber.get('baslik', '')
        url = haber.get('link', '')
        source = haber.get('kaynak', 'Anitrendz')
        image_url = haber.get('resim', '')

        print(f"📤 Paylaşılıyor: {title[:80]}...")

        if post_to_threads(access_token, user_id, title, url, source, image_url):
            print(f"✅ Başarılı: {title}")
            # Her başarılı paylaşımda ID'yi güncelle
            with open(LAST_POSTED_FILE, "w", encoding="utf-8") as f:
                f.write(news_id)
            time.sleep(15)  # Rate limit koruması
        else:
            print(f"❌ Başarısız: {title}")
            break  # Hata olursa dur

if __name__ == "__main__":
    main()
