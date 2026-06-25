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
        print(f"Paylaşım oluşturulamadı: {create_res.text}")
        return False
        
    container_id = create_res.json().get('id')
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    pub_res = requests.post(publish_url, data={"creation_id": container_id, "access_token": access_token})
    
    if pub_res.status_code != 200:
        print(f"Yayınlanamadı: {pub_res.text}")
        return False
    return True

def main():
    access_token = get_working_token()
    if not access_token:
        print("Hata: Erişim token'ı bulunamadı!")
        return

    last_posted_file = "last_posted_threads.txt"
    last_posted_id = None
    if os.path.exists(last_posted_file):
        with open(last_posted_file, "r", encoding="utf-8") as f:
            last_posted_id = f.read().strip()
            if not last_posted_id:
                last_posted_id = None

    # Haberleri yükle
    with open("liste.json", 'r', encoding='utf-8') as f:
        news_list = json.load(f)

    if not news_list:
        print("liste.json boş, çıkılıyor.")
        return

    # En yeni haberler en başta olacak şekilde ters çevir
    news_list.reverse()

    # ----- YENİ HABERLERİ BUL (Bluesky'daki mantık) -----
    yeni_haberler = []
    for haber in news_list:
        haber_id = haber.get('id', '')
        if str(haber_id) == last_posted_id:
            break  # eşleşen ID'ye ulaştık, daha eski haberleri alma
        yeni_haberler.append(haber)

    # Eğer hiç yeni haber yoksa çık
    if not yeni_haberler:
        print("Yeni haber yok, çıkılıyor.")
        return

    # İlk çalışma (last_posted_id yok) – flood olmaması için sadece son 3 haberi paylaş
    if last_posted_id is None:
        print("İlk çalışma, son 3 haber paylaşılacak (flood önlemi).")
        yeni_haberler = yeni_haberler[:3]

    # Haberleri kronolojik sırayla (eskiden yeniye) paylaşmak için ters çevir
    # (Çünkü yeni_haberler şu an en yeni başta, ama paylaşım sırası önemli değil, 
    #  isterseniz doğrudan da paylaşabilirsiniz. Ben eski→yeni olsun diye reverse ekledim.)
    yeni_haberler.reverse()

    # User ID'sini al
    user_id = requests.get(f"https://graph.threads.net/v1.0/me?access_token={access_token}").json().get('id')
    if not user_id:
        print("Kullanıcı ID alınamadı!")
        return

    for haber in yeni_haberler:
        news_id = haber.get('id', '')
        title = haber.get('baslik', '')
        url = haber.get('link', '')
        source = haber.get('kaynak', 'Anitrendz')
        image_url = haber.get('resim', '')

        if post_to_threads(access_token, user_id, title, url, source, image_url):
            print(f"Paylaşıldı: {title}")
            # Her başarılı paylaşımdan sonra son ID'yi güncelle (ileride hata durumunda kaldığı yerden devam eder)
            with open(last_posted_file, "w", encoding="utf-8") as f:
                f.write(str(news_id))
            time.sleep(15)  # spam koruması
        else:
            print(f"Paylaşım başarısız: {title}")

if __name__ == "__main__":
    main()
