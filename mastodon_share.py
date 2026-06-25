import os
import json
import time
import io
import mimetypes
import urllib.request
from mastodon import Mastodon

LISTE_FILE = "liste.json"
LAST_POSTED_FILE = "last_posted_mastodon.txt"


def get_image_bytes(image_url):
    """İnternetten ya da yerel diskten görsel verisini oku."""
    if image_url.startswith("http"):
        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.read()
    else:
        with open(image_url, "rb") as f:
            return f.read()


def build_status_text(title, url, kaynak):
    """Mastodon'un karakter sınırına göre metni hazırla/kırp."""
    full_text = f"📰 {title}\n\nKaynak: {kaynak}\n{url}"

    LIMIT = 480  # Mastodon varsayılan sınırı 500, link/biçim için pay bırakıyoruz
    if len(full_text) > LIMIT:
        overflow = len(full_text) - LIMIT
        shortened_title = title[: max(0, len(title) - overflow - 3)] + "..."
        full_text = f"📰 {shortened_title}\n\nKaynak: {kaynak}\n{url}"

    return full_text


def main():
    api_base_url = os.environ.get("MASTODON_API_BASE_URL")
    access_token = os.environ.get("MASTODON_ACCESS_TOKEN")

    if not api_base_url or not access_token:
        print("❌ Hata: MASTODON_API_BASE_URL veya MASTODON_ACCESS_TOKEN eksik (Secret'lar eksik)!")
        return

    try:
        mastodon = Mastodon(access_token=access_token, api_base_url=api_base_url)
        print(f"Mastodon bağlantısı kuruldu ({api_base_url}), paylaşımlar başlatılıyor...")
    except Exception as e:
        print(f"❌ Mastodon'a bağlanılamadı: {e}")
        return

    try:
        with open(LISTE_FILE, "r", encoding="utf-8") as f:
            haberler = json.load(f)
        if not haberler:
            print("❌ liste.json boş.")
            return
    except Exception as e:
        print(f"❌ liste.json okunurken hata oluştu: {e}")
        return

    last_posted_id = None
    if os.path.exists(LAST_POSTED_FILE):
        with open(LAST_POSTED_FILE, "r", encoding="utf-8") as f:
            last_posted_id = f.read().strip()

    # Son paylaşılandan bu yana eklenen tüm haberleri bul
    yeni_haberler = []
    for haber in haberler:
        haber_id = str(haber.get("id", ""))
        if last_posted_id and haber_id == last_posted_id:
            break
        yeni_haberler.append(haber)

    if not yeni_haberler:
        print("✅ Yeni haber bulunamadı.")
        return

    # İlk çalışmada flood olmasın diye sadece son 3 haber
    if not last_posted_id:
        print("İlk çalışma algılandı, flood olmaması için son 3 haber paylaşılacak...")
        yeni_haberler = yeni_haberler[:3]

    # Eskiden yeniye doğru sırala
    yeni_haberler.reverse()

    for haber in yeni_haberler:
        haber_id = str(haber.get("id", ""))
        title = haber.get("baslik") or haber.get("title")
        url = haber.get("link") or haber.get("url") or ""
        kaynak = haber.get("kaynak", "Anitrendz")
        image_url = haber.get("resim") or haber.get("image") or haber.get("gorsel")

        if not title or not haber_id:
            continue

        status_text = build_status_text(title, url, kaynak)

        try:
            media_ids = None
            if image_url:
                img_data = get_image_bytes(image_url)
                mime_type, _ = mimetypes.guess_type(image_url)
                media = mastodon.media_post(
                    io.BytesIO(img_data),
                    mime_type=mime_type or "image/jpeg",
                    description=title,
                    synchronous=True,
                )
                media_ids = [media["id"]]

            mastodon.status_post(status=status_text, media_ids=media_ids)
            print(f"✅ Başarıyla paylaşıldı: {title[:50]}...")

            # Her başarılı paylaşımdan sonra ID'yi kaydet
            with open(LAST_POSTED_FILE, "w", encoding="utf-8") as f:
                f.write(haber_id)

            # Mastodon hız limitlerine takılmamak için bekle
            time.sleep(5)

        except Exception as e:
            print(f"❌ Paylaşım başarısız (ID: {haber_id}): {e}")
            break


if __name__ == "__main__":
    main()
