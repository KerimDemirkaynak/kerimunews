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
    # Haberi istediğiniz formatta birleştiriyoruz
    full_text = f"{title}\n\nKaynak: {source}\n{url}"
    
    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    
    payload = {"text": full_text, "access_token": access_token}
    
    if image_url and image_url.startswith("http"):
        payload.update({"media_type": "IMAGE", "image_url": image_url})
    else:
        payload.update({"media_type": "TEXT"})
    
    create_res = requests.post(create_url, data=payload)
    if create_res.status_code != 200:
        print(f"Hata: {create_res.text}")
        return False
        
    container_id = create_res.json().get('id')
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    pub_res = requests.post(publish_url, data={"creation_id": container_id, "access_token": access_token})
    
    return pub_res.status_code == 200

def main():
    access_token = get_working_token()
    last_posted_file = "last_posted_threads.txt"
    
    # ID string olduğu için doğrudan okuyoruz
    last_posted_id = ""
    if os.path.exists(last_posted_file):
        with open(last_posted_file, "r") as f:
            last_posted_id = f.read().strip()
            
    with open("liste.json", 'r', encoding='utf-8') as f:
        news_list = json.load(f)
    
    # Eskiden yeniye sıralıyoruz (reverse), böylece en yeni haber en son paylaşılır
    news_list.reverse()
    
    user_id = requests.get(f"https://graph.threads.net/v1.0/me?access_token={access_token}").json().get('id')
    
    for news in news_list:
        news_id = news.get('id', '')
        
        # ID karşılaştırmasını string üzerinden yapıyoruz
        if news_id != last_posted_id:
            title = news.get('baslik', '')
            url = news.get('link', '') # liste.json'da 'link' kullanılmış
            source = news.get('kaynak', 'Anitrendz')
            image_url = news.get('resim', '')
            
            if post_to_threads(access_token, user_id, title, url, source, image_url):
                print(f"Paylaşıldı: {title}")
                with open(last_posted_file, "w") as f:
                    f.write(news_id)
                time.sleep(15) # Paylaşımlar arası spam koruması
        else:
            # last_posted_id'ye ulaştığımızda döngüden çıkabiliriz veya devam edebiliriz
            continue

if __name__ == "__main__":
    main()
