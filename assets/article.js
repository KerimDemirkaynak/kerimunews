/* Kerimu Haber — haber detay sayfası */
(function () {
    'use strict';
    const { clean, esc, decode, toast, setMeta, reducedMotion } = window.Kerimu;

    const SITE = 'https://kerimdemirkaynak.github.io/kerimunews/';
    const articleEl = document.getElementById('news-content');
    const widgetEl = document.getElementById('widget-news-container');

    /* ---------- RSS'ten gelen gövde için basit temizleyici ---------- */
    // Metin düz yazıysa paragraflara böler; HTML içeriyorsa yalnızca güvenli etiketlere izin verir.
    const ALLOWED = new Set(['P', 'BR', 'STRONG', 'B', 'EM', 'I', 'A', 'UL', 'OL', 'LI', 'BLOCKQUOTE', 'H2', 'H3', 'H4']);
    function sanitize(node) {
        Array.from(node.childNodes).forEach(child => {
            if (child.nodeType === 8) { child.remove(); return; }
            if (child.nodeType !== 1) return;
            if (!ALLOWED.has(child.tagName)) {
                if (/^(SCRIPT|STYLE|IFRAME|OBJECT|EMBED)$/.test(child.tagName)) { child.remove(); return; }
                sanitize(child);
                child.replaceWith(...child.childNodes);
                return;
            }
            Array.from(child.attributes).forEach(a => {
                const keep = child.tagName === 'A' && a.name === 'href' && /^(https?:|mailto:)/i.test(a.value.trim());
                if (!keep) child.removeAttribute(a.name);
            });
            if (child.tagName === 'A') { child.target = '_blank'; child.rel = 'noopener noreferrer'; }
            sanitize(child);
        });
    }
    function buildBody(text) {
        const wrap = document.createElement('div');
        const hasHTML = /<\/?(p|br|a|strong|em|b|i|ul|ol|li|h[2-4]|blockquote)\b/i.test(text);
        if (hasHTML) {
            wrap.innerHTML = text;
            sanitize(wrap);
        } else {
            text.split('\n').map(p => p.trim()).filter(Boolean).forEach(p => {
                const el = document.createElement('p');
                el.textContent = decode(p);
                wrap.appendChild(el);
            });
        }
        return wrap.innerHTML;
    }

    /* ---------- Sesli okuma ---------- */
    // Destek yoksa buton HİÇ üretilmez (CSS ile gizlemeye çalışmıyoruz).
    const TTS_OK = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
    const synth = TTS_OK ? window.speechSynthesis : null;
    const LABEL = {
        idle: '<i class="fa-solid fa-volume-high" aria-hidden="true"></i> Haberi Sesli Dinle',
        loading: '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Ses Hazırlanıyor...',
        playing: '<i class="fa-solid fa-stop" aria-hidden="true"></i> Dinlemeyi Durdur'
    };
    let ttsRun = 0;

    function setTts(btn, state) {
        btn.dataset.state = state;
        btn.innerHTML = LABEL[state];
        btn.setAttribute('aria-pressed', String(state === 'playing'));
    }

    // Uzun metin bazı tarayıcılarda ~15 sn sonra kesilir → cümle gruplarına böl
    function chunk(text) {
        const parts = text.replace(/\s+/g, ' ').match(/[^.!?…]+[.!?…]*\s*/g) || [text];
        const out = []; let cur = '';
        parts.forEach(s => {
            if ((cur + s).length > 220 && cur) { out.push(cur); cur = s; } else { cur += s; }
        });
        if (cur.trim()) out.push(cur);
        return out;
    }

    function toggleTts(btn) {
        if (btn.dataset.state !== 'idle') {          // oynuyor ya da hazırlanıyor → durdur
            ttsRun++; synth.cancel(); setTts(btn, 'idle'); return;
        }
        const run = ++ttsRun;
        const text = document.getElementById('okunacak-metin').innerText;
        const chunks = chunk(text);
        setTts(btn, 'loading');

        let started = false, waited = 0;
        const watchdog = setInterval(() => {
            waited += 300;
            if (run !== ttsRun) { clearInterval(watchdog); return; }
            if (started || synth.speaking) {
                clearInterval(watchdog); started = true; setTts(btn, 'playing');
            } else if (waited >= 12000) {
                clearInterval(watchdog); ttsRun++; synth.cancel(); setTts(btn, 'idle');
                toast('Bu tarayıcı cihazın ses motoruna erişemiyor. Standart bir tarayıcı deneyin.');
            }
        }, 300);

        chunks.forEach((c, i) => {
            const u = new SpeechSynthesisUtterance(c);
            u.lang = 'tr-TR'; u.rate = 1.0;
            u.onstart = () => { if (run === ttsRun && !started) { started = true; clearInterval(watchdog); setTts(btn, 'playing'); } };
            u.onend = () => { if (run === ttsRun && i === chunks.length - 1) { clearInterval(watchdog); setTts(btn, 'idle'); } };
            u.onerror = ev => {
                if (run !== ttsRun || ev.error === 'canceled' || ev.error === 'interrupted') return;
                clearInterval(watchdog); ttsRun++; synth.cancel(); setTts(btn, 'idle');
                toast('Sesli okuma başlatılamadı.');
            };
            synth.speak(u);
        });
    }
    window.addEventListener('pagehide', () => { if (synth) synth.cancel(); });

    /* ---------- Paylaş / kopyala ---------- */
    async function copyLink() {
        try {
            await navigator.clipboard.writeText(location.href);
            toast('Bağlantı panoya kopyalandı');
        } catch (e) {
            toast('Kopyalanamadı — adres çubuğundan kopyalayabilirsiniz');
        }
    }

    /* ---------- Meta etiketleri (sosyal medya + SEO) ---------- */
    function applyMeta(h, description) {
        const title = `${decode(h.baslik)} - Kerimu Animasyon`;
        const url = location.href;
        const image = h.resim && /^https?:/i.test(h.resim) ? h.resim : SITE + 'assets/og-image.png';
        document.title = title;
        setMeta('meta[name="description"]', 'content', description);
        setMeta('link[rel="canonical"]', 'href', url);
        setMeta('meta[property="og:title"]', 'content', decode(h.baslik));
        setMeta('meta[property="og:description"]', 'content', description);
        setMeta('meta[property="og:url"]', 'content', url);
        setMeta('meta[property="og:image"]', 'content', image);
        setMeta('meta[property="og:image:alt"]', 'content', decode(h.baslik));
        setMeta('meta[name="twitter:title"]', 'content', decode(h.baslik));
        setMeta('meta[name="twitter:description"]', 'content', description);
        setMeta('meta[name="twitter:image"]', 'content', image);

        const ld = document.createElement('script');
        ld.type = 'application/ld+json';
        ld.textContent = JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'NewsArticle',
            headline: decode(h.baslik),
            image: [image],
            author: { '@type': 'Person', name: 'Kerim Demirkaynak', url: 'https://github.com/KerimDemirkaynak' },
            publisher: { '@type': 'Organization', name: 'Kerimu Animasyon Haberleri', logo: { '@type': 'ImageObject', url: SITE + 'assets/icon-512.png' } },
            mainEntityOfPage: url,
            description
        });
        document.head.appendChild(ld);
    }

    /* ---------- Yan panel ---------- */
    async function loadWidget(currentId) {
        try {
            const res = await fetch('liste.json');
            if (!res.ok) throw new Error();
            const all = await res.json();
            const list = all.filter(h => h.id !== currentId).slice(0, 6);
            if (!list.length) { widgetEl.innerHTML = '<p class="widget-empty">Başka haber bulunamadı.</p>'; return; }
            widgetEl.innerHTML = list.map((h, i) => {
                const img = h.resim
                    ? `<img src="${esc(h.resim)}" alt="" class="widget-img" loading="lazy" decoding="async" width="64" height="64">`
                    : `<div class="widget-img">${clean(h.kaynak)}</div>`;
                return `
                    <a href="haber.html?id=${encodeURIComponent(h.id)}" class="widget-item" style="--i:${i}">
                        ${img}
                        <div class="widget-text-container">
                            <h4 class="widget-item-title">${clean(h.baslik)}</h4>
                            <span class="widget-item-meta">${clean(h.tarih)}</span>
                        </div>
                    </a>`;
            }).join('');
        } catch (e) {
            widgetEl.innerHTML = '<p class="widget-empty">Haberler yüklenemedi.</p>';
        }
    }

    /* ---------- Yorumlar ---------- */
    function loadGiscus() {
        const container = document.getElementById('giscus-container');
        if (!container) return;
        const s = document.createElement('script');
        s.src = 'https://giscus.app/client.js';
        const attrs = {
            'data-repo': 'KerimDemirkaynak/Yorumlar', 'data-repo-id': 'R_kgDOPPm0QA',
            'data-category': 'Yorumlar', 'data-category-id': 'DIC_kwDOPPm0QM4CtM73',
            'data-mapping': 'url', 'data-strict': '0', 'data-reactions-enabled': '1',
            'data-emit-metadata': '0', 'data-input-position': 'top',
            'data-theme': 'transparent_dark', 'data-lang': 'tr', 'crossorigin': 'anonymous'
        };
        Object.entries(attrs).forEach(([k, v]) => s.setAttribute(k, v));
        s.async = true;
        container.appendChild(s);
    }

    /* ---------- Haberi getir ---------- */
    function showError(msg) {
        articleEl.innerHTML = `<div class="state-box"><h3>${esc(msg)}</h3><p>Ana sayfaya dönüp başka bir habere göz atabilirsiniz.</p></div>`;
    }

    async function load() {
        const id = new URLSearchParams(location.search).get('id');
        if (!id) { showError('Haber bulunamadı.'); widgetEl.innerHTML = ''; return; }
        loadWidget(id);

        try {
            const res = await fetch(`haberler/${encodeURIComponent(id)}.json`);
            if (!res.ok) throw new Error('Haber dosyası bulunamadı.');
            const h = await res.json();

            const plain = decode(String(h.tamMetin || '').replace(/<[^>]*>/g, ' ')).replace(/\s+/g, ' ').trim();
            const minutes = Math.max(1, Math.ceil((plain ? plain.split(' ').length : 0) / 200));
            const description = plain.length > 160 ? plain.slice(0, 157).replace(/\s+\S*$/, '') + '…' : plain;
            applyMeta(h, description);

            const pageUrl = encodeURIComponent(location.href);
            const title = encodeURIComponent(decode(h.baslik));
            const hasImg = h.resim && /^https?:/i.test(h.resim);
            const orig = /^https?:/i.test(h.link || '') ? esc(h.link) : null;

            articleEl.classList.add('is-entering');
            articleEl.innerHTML = `
                ${hasImg ? `<img src="${esc(h.resim)}" alt="" class="article-image" width="1200" height="630">` : ''}
                <div class="article-header"><h1 class="article-title">${clean(h.baslik)}</h1></div>

                <div class="article-sub-bar">
                    <div class="author-meta-top">
                        <a href="https://github.com/KerimDemirkaynak" target="_blank" rel="noopener noreferrer">
                            <img src="https://avatars.githubusercontent.com/u/76594465?v=4&size=64" alt="Kerim Demirkaynak" width="46" height="46">
                        </a>
                        <div class="author-info">
                            <a href="https://github.com/KerimDemirkaynak" target="_blank" rel="noopener noreferrer" class="author-name">Kerim Demirkaynak</a>
                            <span class="author-date">${clean(h.tarih)}</span>
                        </div>
                    </div>
                    <div class="article-source">
                        <div>Kaynak: <strong>${clean(h.kaynak)}</strong></div>
                        <div>Tür: <strong>${clean(h.kategori)}</strong></div>
                        <div><i class="fa-regular fa-clock" aria-hidden="true"></i> Okuma Süresi: <strong>${minutes} dk</strong></div>
                    </div>
                </div>

                <div class="article-body">
                    ${TTS_OK ? '<button type="button" id="tts-btn" class="tts-btn"></button>' : ''}
                    <div id="okunacak-metin" class="article-text">${buildBody(String(h.tamMetin || ''))}</div>
                    ${orig ? `<a href="${orig}" target="_blank" rel="noopener noreferrer" class="original-link">Orijinal Habere Git <i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i></a>` : ''}

                    <div class="social-share">
                        <span class="share-text">Haberi Paylaş:</span>
                        <div class="share-buttons-container">
                            <a href="https://twitter.com/intent/tweet?url=${pageUrl}&text=${title}" target="_blank" rel="noopener noreferrer" class="icon-btn share-btn btn-twitter" aria-label="X'te paylaş" title="X'te paylaş"><i class="fa-brands fa-x-twitter" aria-hidden="true"></i></a>
                            <a href="https://www.facebook.com/sharer/sharer.php?u=${pageUrl}" target="_blank" rel="noopener noreferrer" class="icon-btn share-btn btn-facebook" aria-label="Facebook'ta paylaş" title="Facebook'ta paylaş"><i class="fa-brands fa-facebook-f" aria-hidden="true"></i></a>
                            <a href="https://api.whatsapp.com/send?text=${encodeURIComponent(decode(h.baslik) + ' ' + location.href)}" target="_blank" rel="noopener noreferrer" class="icon-btn share-btn btn-whatsapp" aria-label="WhatsApp'tan gönder" title="WhatsApp'tan gönder"><i class="fa-brands fa-whatsapp" aria-hidden="true"></i></a>
                            <a href="https://t.me/share/url?url=${pageUrl}&text=${title}" target="_blank" rel="noopener noreferrer" class="icon-btn share-btn btn-telegram" aria-label="Telegram'da paylaş" title="Telegram'da paylaş"><i class="fa-brands fa-telegram" aria-hidden="true"></i></a>
                            <button type="button" id="copy-btn" class="icon-btn share-btn btn-copy" aria-label="Bağlantıyı kopyala" title="Bağlantıyı kopyala"><i class="fa-solid fa-link" aria-hidden="true"></i></button>
                        </div>
                    </div>

                    <div class="author-card">
                        <a href="https://github.com/KerimDemirkaynak" target="_blank" rel="noopener noreferrer">
                            <img src="https://avatars.githubusercontent.com/u/76594465?v=4&size=64" alt="Kerim Demirkaynak" width="80" height="80">
                        </a>
                        <div class="author-card-text">
                            <a href="https://github.com/KerimDemirkaynak" target="_blank" rel="noopener noreferrer" class="author-card-name">Kerim Demirkaynak</a>
                            <p>Yazılım geliştirici, açık kaynak katılımcısı ve vibe coder. Anime dünyasına olan ilgisini teknolojiyle birleştirerek içerikler üretiyor.</p>
                        </div>
                    </div>
                </div>`;

            const img = articleEl.querySelector('.article-image');
            if (img) { img.complete && img.naturalWidth ? img.classList.add('loaded') : (img.onload = () => img.classList.add('loaded'), img.onerror = () => img.remove()); }

            const ttsBtn = document.getElementById('tts-btn');
            if (ttsBtn) { setTts(ttsBtn, 'idle'); ttsBtn.addEventListener('click', () => toggleTts(ttsBtn)); }
            document.getElementById('copy-btn').addEventListener('click', copyLink);

            loadGiscus();
        } catch (err) {
            console.error('Hata:', err);
            showError('Haber metni yüklenemedi veya silinmiş olabilir.');
        }
    }

    load();
})();
