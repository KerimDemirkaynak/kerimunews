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
    # Metni birleştir
    full_text = f"{title}\n\nKaynak: {source}\n{url}"
    
    # 500 karakter sınırına karşı metni kısaltma kontrolü
    if len(full_text) > 480:
        # Başlığı, linke yer kalacak şekilde kırp
        overflow = len(full_text) - 480
        shortened_title = title[:-overflow-3] + "..."
        full_text = f"{shortened_title}\n\nKaynak: {source}\n{url}"

    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    payload = {
        "text": full_text,
        "access_token": access_token,
        "media_type": "IMAGE" if image_url and image_url.startswith("http") else "TEXT"
    }
    if payload["media_type"] == "IMAGE":
        payload["image_url"] = image_url

    create_res = requests.post(create_url, data=payload)
    if create_res.status_code != 200:
        print(f"❌ Oluşturma hatası: {create_res.text}")
        return False

    container_id = create_res.json().get('id')
    if not container_id:
        return False

    pub_res = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        data={"creation_id": container_id, "access_token": access_token}
    )
    
    return pub_res.status_code == 200

def main():
    access_token = get_working_token()
    if not access_token:
        print("❌ Token bulunamadı!")
        return

    last_posted_id = None
    if os.path.exists(LAST_POSTED_FILE):
        with open(LAST_POSTED_FILE, "r", encoding="utf-8") as f:
            last_posted_id = f.read().strip()

    with open("liste.json", 'r', encoding='utf-8') as f:
        news_list = json.load(f)

    if not news_list:
        print("❌ liste.json boş.")
        return

    # Son paylaşılandan sonraki yeni haberleri topla
    yeni_haberler = []
    for haber in news_list:
        haber_id = str(haber.get('id', ''))
        if last_posted_id and haber_id == last_posted_id:
            break
        yeni_haberler.append(haber)

    if not yeni_haberler:
        print("✅ Yeni haber yok.")
        return

    # İlk çalıştırma ise son 5 haber
    if not last_posted_id:
        yeni_haberler = yeni_haberler[:5]

    # Eskiden yeniye doğru sırala
    yeni_haberler.reverse()

    # User ID'yi al
    me = requests.get(f"https://graph.threads.net/v1.0/me?access_token={access_token}").json()
    user_id = me.get('id')
    if not user_id:
        print("❌ User ID alınamadı!")
        return

    # Sırayla paylaş
    for haber in yeni_haberler:
        haber_id = str(haber.get('id', ''))
        title = haber.get('baslik', '')
        url = haber.get('link', '')
        source = haber.get('kaynak', 'Anitrendz')
        image_url = haber.get('resim', '')

        print(f"📤 Paylaşılıyor → {title[:50]}...")

        if post_to_threads(access_token, user_id, title, url, source, image_url):
            print(f"✅ Paylaşıldı: {haber_id}")
            with open(LAST_POSTED_FILE, "w", encoding="utf-8") as f:
                f.write(haber_id)
            time.sleep(18)
        else:
            print(f"❌ Paylaşım başarısız: {haber_id}")
            break

if __name__ == "__main__":
    main()
