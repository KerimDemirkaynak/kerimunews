import os
import json
import requests

def get_threads_user_id(access_token):
    """Erişim belirteci ile Threads kullanıcı ID'sini alır."""
    url = f"https://graph.threads.net/v1.0/me?access_token={access_token}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('id')
    else:
        print(f"Kullanıcı ID alınamadı: {response.text}")
        return None

def post_to_threads(access_token, user_id, text, link):
    """Threads'e metin ve bağlantı içeren bir gönderi atar."""
    # Threads post metnini oluştur (Başlık + Link)
    full_text = f"{text}\n\n{link}"
    
    # 1. Adım: Bir Threads kapsayıcısı (container) oluştur
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
    print(f"Kapsayıcı oluşturuldu (ID: {container_id})")
    
    # 2. Adım: Kapsayıcıyı yayınla (Publish)
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
    ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN")
    if not ACCESS_TOKEN:
        print("Hata: THREADS_ACCESS_TOKEN ortam değişkeni bulunamadı.")
        return

    # En güncel haberleri liste.json'dan çek
    list_file = "liste.json"
    if not os.path.exists(list_file):
        print("liste.json bulunamadı!")
        return
        
    with open(list_file, 'r', encoding='utf-8') as f:
        news_list = json.load(f)
        
    if not news_list:
        print("Paylaşılacak haber bulunamadı.")
        return
        
    # En güncel haber (listenin en başındaki)
    latest_news = news_list[0]
    title = latest_news.get('baslik', '')
    url = latest_news.get('url', '')
    news_id = latest_news.get('id', '')
    
    # Aynı haberi tekrar paylaşmamak için kontrol et
    last_posted_file = "last_posted_threads.txt"
    last_posted_id = ""
    if os.path.exists(last_posted_file):
        with open(last_posted_file, "r") as f:
            last_posted_id = f.read().strip()
            
    if news_id == last_posted_id:
        print("En güncel haber Threads'te zaten paylaşılmış. Atlanıyor.")
        return

    # Kullanıcı ID'sini al
    user_id = get_threads_user_id(ACCESS_TOKEN)
    if not user_id:
        return
        
    # Haberi paylaş
    success = post_to_threads(ACCESS_TOKEN, user_id, title, url)
    
    # Başarılı olursa ID'yi txt dosyasına kaydet
    if success:
        with open(last_posted_file, "w") as f:
            f.write(news_id)

if __name__ == "__main__":
    main()
