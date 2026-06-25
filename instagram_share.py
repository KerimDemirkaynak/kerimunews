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

def get_working_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token: return token
    return os.environ.get("IG_ACCESS_TOKEN")

def build_caption(title, ozet, kaynak, tarih, kategori):
    """Başlık, özet ve diğer bilgileri birleştirir."""
    # Metni oluştur (başlık + özet)
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
    # Toplam metin sınırını kontrol et
    if len(body) + len(tail) > LIMIT:
        available_space = LIMIT - len(tail) - 3
        body = body[:available_space] + "..."

    return f"{body}{tail}"

# ... (Daha önce paylaşılan diğer yardımcı fonksiyonlar: get_image_bytes, crop_for_instagram, create_container, wait_until_finished aynı kalmalı)

def main():
    # ... (Main fonksiyonu içerisinde haberleri okurken)
    # title = haber.get("baslik")
    # ozet = haber.get("ozet")
    # ...
    # caption = build_caption(title, ozet, kaynak, tarih, kategori)
    # ...
    pass

if __name__ == "__main__":
    main()
