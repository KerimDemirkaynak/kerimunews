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
        return False
        
    container_id = create_res.json().get('id')
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    pub_res = requests.post(publish_url, data={"creation_id": container_id, "access_token": access_token})
    return pub_res.status_code == 200

def main():
    access_token = get_working_token()
    last_posted_file = "last_posted_threads.txt"
    
    # 1. Mevcut son ID'yi al
    last_posted_id = ""
    if os.path.exists(last_posted_file):
        with open(last_posted_file, "r") as f:
            last_posted_id = f.read().strip()
            
    # 2. Haberleri yükle
    with open("liste.json", 'r', encoding='utf-8') as f:
        news_list = json.load(f)
    
    # 3. Yeni haberleri belirle (Yeni'den eskiye sıralı varsayarak: news_list[0] en yeni)
    # Eğer listeniz zaten [En Yeni, ..., En Eski] şeklindeyse:
    new_posts = []
    for news in news_list:
        if news.get('id') == last_posted_id:
            break # Eşleştiğimiz an dur, eski haberleri geçme
        new_posts.append(news)
    
    # 4. Haberleri eskiden yeniye paylaş ki en son paylaşılan ID "en yeni" olsun
    new_posts.reverse()
    
    user_id = requests.get(f"https://graph.threads.net/v1.0/me?access_token={access_token}").json().get('id')
    
    for news in new_posts:
        title = news.get('baslik', '')
        url = news.get('link', '')
        source = news.get('kaynak', 'Anitrendz')
        image_url = news.get('resim', '')
        
        if post_to_threads(access_token, user_id, title, url, source, image_url):
            print(f"Paylaşıldı: {title}")
            # Döngü bittikten sonra değil, her başarılı paylaşımda ID'yi güncelle
            with open(last_posted_file, "w") as f:
                f.write(news.get('id', ''))
            time.sleep(15) 

if __name__ == "__main__":
    main()
