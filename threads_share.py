import os
import json
import requests

TOKEN_FILE = "threads_token.txt"

def get_working_token():
    """
    Öncelikle yerelde kayıtlı güncel bir token dosyası var mı bakar.
    Yoksa GitHub Secrets'tan gelen ilk token'ı kullanır.
    """
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            saved_token = f.read().strip()
            if saved_token:
                return saved_token
    return os.environ.get("THREADS_ACCESS_TOKEN")

def refresh_threads_token(current_token, app_secret):
    """
    Threads uzun süreli erişim belirtecini (Long-Lived Token) yeniler.
    Yenilenen token'ı yerel dosyaya yazar.
    """
    if not current_token or not app_secret:
        return current_token

    url = "https://graph.threads.net/refresh_access_token"
    params = {
        "grant_type": "th_refresh_token",
        "access_token": current_token
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            new_token = response.json().get("access_token")
            if new_token:
                with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                    f.write(new_token)
                print("Threads Access Token başarıyla yenilendi ve kaydedildi.")
                return new_token
        else:
            print(f"Token yenilenemedi (Paylaşıma eski token ile devam ediliyor): {response.text}")
    except Exception as e:
        print(f"Token yenileme sırasında hata oluştu: {e}")
        
    return current_token

def get_threads_user_id(access_token):
    url = f"https://graph.threads.net/v1.0/me?access_token={access_token}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('id')
    else:
        print(f"Kullanıcı ID alınamadı: {response.text}")
        return None

def post_to_threads(access_token, user_id, text, link):
    full_text = f"{text}\n\n{link}"
    
    # 1. Adım: Kapsayıcı oluştur
    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    payload = {
        "media_type": "TEXT",
        "text": full_text,
        "access_token": access_token
    }
    
    create_res = requests.post(create_url, data=payload)
    if create_res.status_code != 200:
        print(f"Kapsayıcı oluşturma hatası: {create_res.text}")
        return False
        
    container_id = create_res.json().get('id')
    
    # 2. Adım: Yayınla
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    pub_payload = {
        "creation_id": container_id,
        "access_token": access_token
    }
    
    pub_res = requests.post(publish_url, data=pub_payload)
    if pub_res.status_code != 200:
        print(f"Yayınlama hatası: {pub_res.text}")
        return False
        
    print(f"Threads üzerinde başarıyla paylaşıldı! Post ID: {pub_res.json().get('id')}")
    return True

def main():
    APP_SECRET = os.environ.get("THREADS_APP_SECRET")
    
    # Güncel çalışma token'ını tespit et
    access_token = get_working_token()
    if not access_token:
        print("Hata: Threads erişim belirteci bulunamadı.")
        return

    # liste.json'dan en güncel haberi çek
    list_file = "liste.json"
    if not os.path.exists(list_file):
        print("liste.json bulunamadı!")
        return
        
    with open(list_file, 'r', encoding='utf-8') as f:
        news_list = json.load(f)
        
    if not news_list:
        print("Paylaşılacak haber bulunamadı.")
        return
        
    latest_news = news_list[0]
    title = latest_news.get('baslik', '')
    url = latest_news.get('url', '')
    news_id = latest_news.get('id', '')
    
    # Tekrar paylaşımı engelleme kontrolü
    last_posted_file = "last_posted_threads.txt"
    last_posted_id = ""
    if os.path.exists(last_posted_file):
        with open(last_posted_file, "r") as f:
            last_posted_id = f.read().strip()
            
    if news_id == last_posted_id:
        print("En güncel haber Threads'te zaten paylaşılmış. Atlanıyor.")
        # Haber yeni olmasa bile token'ı arka planda yenileyelim ki güncel kalsın
        refresh_threads_token(access_token, APP_SECRET)
        return

    # Kullanıcı ID'sini al
    user_id = get_threads_user_id(access_token)
    if not user_id:
        return
        
    # Haberi paylaş
    success = post_to_threads(access_token, user_id, title, url)
    
    if success:
        with open(last_posted_file, "w") as f:
            f.write(news_id)
        # Paylaşım başarılı olduktan sonra token yenileme mekanizmasını tetikle
        refresh_threads_token(access_token, APP_SECRET)

if __name__ == "__main__":
    main()
