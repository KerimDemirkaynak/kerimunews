# 📺 Kerimu Animasyon Haberleri

Dünyanın önde gelen anime ve çizgi film haber kaynaklarını tek bir yerde toplayan, tamamen otomatik ve otonom çalışan Türkçe haber platformu. 

Bu proje, **Headless (Başsız) Statik API** mimarisi kullanılarak inşa edilmiştir. Arka planda çalışan Python botu, haberleri çeker, çevirir ve statik JSON dosyaları üreterek GitHub Pages üzerinden ışık hızında sunar.

🔗 **Canlı Site:** https://kerimdemirkaynak.github.io/kerimunews
<br> 📡 **RSS Beslememiz:** https://kerimdemirkaynak.github.io/kerimunews/rss.xml

## ✨ Öne Çıkan Özellikler

* **🤖 Tam Otomasyon:** GitHub Actions sayesinde her gece yarısı otomatik çalışır.
* **🌍 Otomatik Çeviri:** Yabancı kaynaklardan gelen haber başlıkları, özetleri ve tam metinleri anında Türkçeye çevrilir.
* **⚡ Statik API Mimarisi:** Veritabanı yoktur. Ana sayfa için hafif bir `liste.json`, her haberin detayı için ise `haberler/ID.json` üretilerek sayfa yüklenme hızı maksimize edilir.
* **💬 Modern Yorum Sistemi:** Her haberin altında, GitHub Discussions altyapısını kullanan **Giscus** yorum sistemi bulunur.
* **🎨 Responsive ve Dark Mode:** Mobil uyumlu, göz yormayan modern karanlık tema tasarımı.
* **🛡️ Bot Koruması Aşma:** Bazı haber sitelerinin RSS kısıtlamalarını aşmak için "Stealth (Gizli)" HTTP istekleri kullanılır.

## 📰 Kaynaklarımız

Sistem şu anda aşağıdaki kaynaklardan düzenli olarak veri çekmektedir:
* [Anitrendz](https://anitrendz.net/) (Anime)
* [AnimeHunch](https://animehunch.com/) (Anime)
* [AnimeNewsNetwork](https://www.animenewsnetwork.com/) (Anime)
* [CBR](https://www.cbr.com/) (Anime & Çizgi Film)
* [CartoonBrew](https://www.cartoonbrew.com/) (Çizgi Film)

## ⚙️ Sistem Nasıl Çalışır?

1. **GitHub Actions (`update_news.yml`):** Belirlenen zaman diliminde Ubuntu sunucusunu ayağa kaldırır ve Python betiğini tetikler.
2. **Veri Toplama ve Çeviri (`scraper.py`):** Kaynakların RSS beslemelerini okur, yeni haber varsa web scraping ile tam metni ve yüksek çözünürlüklü kapağı (og:image) çeker. Google Translate mantığıyla metinleri Türkçeye çevirir.
3. **Arşivleme ve API Üretimi:** Çekilen her yeni habere benzersiz bir Hash ID atanır. Ana vitrin için `liste.json` güncellenir, detaylar ise `haberler/ID.json` şeklinde klasörlenir. Ayrıca en güncel 20 haberden oluşan bir `rss.xml` dosyası üretilir.
4. **Yayınlama:** Değişiklikler otomatik olarak GitHub'a push edilir ve GitHub Pages siteyi anında günceller.

## 🛠️ Kurulum ve Geliştirme

Bu projeyi kendi sisteminizde çalıştırmak veya geliştirmek isterseniz:

1. Depoyu klonlayın: `git clone https://github.com/kerimdemirkaynak/kerimunews.git`
2. Gerekli Python kütüphanelerini yükleyin: `pip install -r requirements.txt`
3. Botu manuel test etmek için terminalde çalıştırın: `python scraper.py`

## 📄 Lisans

Bu proje MIT Lisansı kapsamında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakabilirsiniz.
