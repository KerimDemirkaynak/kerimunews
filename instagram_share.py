import os
import json
import time
import io
import subprocess
import requests
from PIL import Image

LISTE_FILE = "liste.json"
LAST_POSTED_FILE = "last_posted_instagram.txt"
TOKEN_FILE = "instagram_token.txt"
IMAGE_DIR = "instagram_uploads"

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

MIN_RATIO = 0.8
MAX_RATIO = 1.91

def setup_git():
    """Git yapılandırmasını ayarlar (actions ortamında çalışırken)."""
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git config ayarlanamadı: {e}")

def get_working_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token:
                return token
    return os.environ.get("IG_ACCESS_TOKEN")

def refresh_token(current_token, app_id, app_secret):
    try:
        resp = requests.get(
            f"{GRAPH_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": current_token,
            },
            timeout=30,
        )
        data = resp.json()
        return data.get("access_token")
    except Exception as e:
        print(f"⚠️ Token yenilenemedi, mevcut token ile devam ediliyor: {e}")
        return None

def git_commit_push(message):
    """instagram_uploads/ klasöründeki değişiklikleri (ekleme/silme) commitleyip pushlar."""
    try:
        subprocess.run(["git", "add", "-A"], check=True)
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
        if result.returncode != 0:
            if "nothing to commit" in result.stderr:
                print("ℹ️ Commit gerektirecek değişiklik yok.")
                return True
            else:
                print(f"⚠️ Commit başarısız: {result.stderr}")
                return False
        subprocess.run(["git", "push"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git işlemi başarısız: {e}")
        return False

def get_image_bytes(url):
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    return resp.content

def crop_for_instagram(img):
    width, height = img.size
    ratio = width / height

    if ratio < MIN_RATIO:
        new_height = int(width / MIN_RATIO)
        top = (height - new_height) // 2
        img = img.crop((0, top, width, top + new_height))
    elif ratio > MAX_RATIO:
        new_width = int(height * MAX_RATIO)
        left = (width - new_width) // 2
        img = img.crop((left, 0, left + new_width, height))

    return img

def build_caption(title, ozet, kaynak, tarih, kategori):
    body = f"{title}\n\n{ozet}"
    
    tail = (
        "\n\nAyrıntılar web sitemizde.\n\n"
        f"Kaynak: {kaynak}\n\n"
        f"Haberin tarihi: {tarih}\n\n"
        f"Kategori: {kategori}\n\n"
        "Güvenilir ve güncel anime haberleri için takip etmeyi ve beğenmeyi unutmayın!\n\n"
        "#anime #animehaber #animehaberleri #animetr #animetürkiye #animehayranı "
        "#animeler #animelover #türkanime #animetürk #turkanime #animeturk "
        "#animasyon #otaku #çizgifilmhaber"
    )

    LIMIT = 2200
    if len(body) + len(tail) > LIMIT:
        available_space = LIMIT - len(tail) - 3
        body = body[:available_space] + "..."

    return f"{body}{tail}"

def create_container(ig_user_id, image_url, caption, access_token):
    last_res = None
    for attempt in range(3):
        resp = requests.post(
            f"{GRAPH_BASE}/{ig_user_id}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": access_token,
            },
            timeout=30,
        )
        last_res = resp.json()
        if last_res.get("id"):
            return last_res.get("id"), None
        time.sleep(5)
    return None, last_res

def wait_until_finished(container_id, access_token):
    status = None
    last_res = None
    for _ in range(10):
        resp = requests.get(
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        last_res = resp.json()
        status = last_res.get("status_code")
        if status in ("FINISHED", "ERROR"):
            break
        time.sleep(3)
    return status, last_res

def main():
    setup_git()  # <-- Git kimlik ayarları eklendi

    ig_user_id = os.environ.get("IG_USER_ID")
    app_id = os.environ.get("IG_APP_ID")
    app_secret = os.environ.get("IG_APP_SECRET")

    if not ig_user_id:
        print("❌ Hata: IG_USER_ID eksik!")
        return

    access_token = get_working_token()
    if not access_token:
        print("❌ Hata: Erişim token'ı bulunamadı (IG_ACCESS_TOKEN secret eksik)!")
        return

    if app_id and app_secret:
        refreshed = refresh_token(access_token, app_id, app_secret)
        if refreshed:
            access_token = refreshed
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(access_token)
            print("🔄 Token yenilendi ve kaydedildi.")

    try:
        with open(LISTE_FILE, "r", encoding="utf-8") as f:
            haberler = json.load(f)
        if not haberler:
            print("❌ liste.json boş.")
            return
    except Exception as e:
        print(f"❌ liste.json okunamadı: {e}")
        return

    last_posted_id = None
    if os.path.exists(LAST_POSTED_FILE):
        with open(LAST_POSTED_FILE, "r", encoding="utf-8") as f:
            last_posted_id = f.read().strip()

    yeni_haberler = []
    for haber in haberler:
        haber_id = str(haber.get("id", ""))
        if last_posted_id and haber_id == last_posted_id:
            break
        yeni_haberler.append(haber)

    if not yeni_haberler:
        print("✅ Yeni haber yok.")
        return

    if not last_posted_id:
        print("İlk çalışma algılandı, flood olmaması için son 3 haber işlenecek...")
        yeni_haberler = yeni_haberler[:3]

    yeni_haberler.reverse()

    os.makedirs(IMAGE_DIR, exist_ok=True)
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("GITHUB_REF_NAME", "main")

    for haber in yeni_haberler:
        haber_id = str(haber.get("id", ""))
        title = haber.get("baslik") or haber.get("title") or ""
        ozet = haber.get("ozet") or haber.get("description") or ""
        kaynak = haber.get("kaynak", "")
        tarih = haber.get("tarih", "")
        kategori = haber.get("kategori", "")
        image_url = haber.get("resim") or haber.get("image") or haber.get("gorsel")

        if not haber_id:
            continue

        if not image_url:
            print(f"⏭️ Görsel yok, atlanıyor: {title[:50]}...")
            with open(LAST_POSTED_FILE, "w", encoding="utf-8") as f:
                f.write(haber_id)
            continue

        local_path = os.path.join(IMAGE_DIR, f"{haber_id}.jpg")

        try:
            img_data = get_image_bytes(image_url)
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            img = crop_for_instagram(img)
            img.save(local_path, "JPEG", quality=90)

            if not repo:
                print("❌ GITHUB_REPOSITORY bulunamadı, görsel URL'si oluşturulamıyor.")
                break

            if not git_commit_push(f"IG görseli eklendi: {haber_id}"):
                print(f"⚠️ Görsel push edilemedi, atlanıyor (ID: {haber_id})")
                continue

            public_image_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{local_path}"
            time.sleep(8)

            caption = build_caption(title, ozet, kaynak, tarih, kategori)
            container_id, err = create_container(ig_user_id, public_image_url, caption, access_token)
            if not container_id:
                print(f"❌ Container oluşturulamadı (ID: {haber_id}): {err}")
                continue

            status, status_res = wait_until_finished(container_id, access_token)
            if status != "FINISHED":
                print(f"❌ Container hazır olmadı (ID: {haber_id}, durum: {status}): {status_res}")
                continue

            publish_res = requests.post(
                f"{GRAPH_BASE}/{ig_user_id}/media_publish",
                data={"creation_id": container_id, "access_token": access_token},
                timeout=30,
            ).json()

            if not publish_res.get("id"):
                print(f"❌ Paylaşım yapılamadı (ID: {haber_id}): {publish_res}")
                continue

            print(f"✅ Instagram'da paylaşıldı: {title[:50]}...")

            with open(LAST_POSTED_FILE, "w", encoding="utf-8") as f:
                f.write(haber_id)

            try:
                os.remove(local_path)
            except OSError:
                pass
            git_commit_push(f"IG görseli temizlendi: {haber_id}")

            time.sleep(10)

        except Exception as e:
            print(f"❌ Paylaşım başarısız (ID: {haber_id}): {e}")
            break

if __name__ == "__main__":
    main()
