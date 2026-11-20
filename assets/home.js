/* Kerimu Haber — ana sayfa */
(function () {
    'use strict';
    const { reducedMotion, clean, esc, fold } = window.Kerimu;

    const PER_PAGE = 9;
    const LEAVE_MS = reducedMotion ? 0 : 160;
    const STORE_KEY = 'kerimu:list-state';

    const grid = document.getElementById('news-container');
    const pager = document.getElementById('pagination-container');
    const filters = document.querySelector('.filters');
    const filterBtns = Array.from(document.querySelectorAll('.filter-btn'));
    const indicator = document.querySelector('.filter-indicator');
    const searchInput = document.getElementById('search-input');
    const totalEl = document.getElementById('toplam-haber-sayisi');

    let allNews = [];
    let category = 'Tümü';
    let query = '';
    let page = 1;
    let renderToken = 0;

    /* ---------- Durumu hatırla (haberden geri dönünce 323. sayfada kalsın) ---------- */
    function saveState() {
        try { sessionStorage.setItem(STORE_KEY, JSON.stringify({ category, query, page })); } catch (e) { /* özel mod vb. */ }
    }
    function restoreState() {
        try {
            const s = JSON.parse(sessionStorage.getItem(STORE_KEY) || 'null');
            if (!s) return;
            if (['Tümü', 'Anime', 'Çizgi Film'].includes(s.category)) category = s.category;
            if (typeof s.query === 'string') query = s.query;
            if (Number.isInteger(s.page) && s.page > 0) page = s.page;
        } catch (e) { /* yoksay */ }
    }

    /* ---------- Filtre göstergesi (kayan kapsül) ---------- */
    function syncFilterUI(animate) {
        filterBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.category === category)));
        const active = filterBtns.find(b => b.dataset.category === category) || filterBtns[0];
        if (!active || !indicator) return;
        if (!animate) filters.classList.remove('ready');
        indicator.style.setProperty('--x', active.offsetLeft + 'px');
        indicator.style.setProperty('--w', active.offsetWidth + 'px');
        if (!animate) { void indicator.offsetWidth; filters.classList.add('ready'); }
    }

    /* ---------- Kart HTML'i ---------- */
    function skeletonCards(n) {
        return Array.from({ length: n }, (_, i) => `
            <div class="news-card glass-card is-skeleton" style="--i:${i}" aria-hidden="true">
                <div class="card-media skeleton"></div>
                <div class="card-content">
                    <div class="skeleton sk-tag"></div>
                    <div class="skeleton sk-title sk-line"></div>
                    <div class="skeleton sk-line sk-w80"></div>
                    <div class="skeleton sk-line"></div>
                    <div class="skeleton sk-line sk-w60"></div>
                </div>
            </div>`).join('');
    }

    function cardHTML(h, i) {
        const tagClass = h.kategori === 'Anime' ? 'tag-anime' : 'tag-cartoon';
        const baslik = clean(h.baslik);
        const media = h.resim
            ? `<img src="${esc(h.resim)}" alt="" loading="lazy" decoding="async" width="600" height="360">`
            : `<span>${clean(h.kaynak)}</span>`;
        return `
            <a class="news-card glass-card" style="--i:${i}" href="haber.html?id=${encodeURIComponent(h.id)}">
                <div class="card-media">${media}</div>
                <div class="card-content">
                    <span class="card-tag ${tagClass}">${clean(h.kategori)}</span>
                    <h2 class="card-title">${baslik}</h2>
                    <p class="card-excerpt">${clean(h.ozet)}</p>
                    <div class="card-footer">
                        <span>${clean(h.tarih)}</span>
                        <span class="read-more-btn">Haberi Oku <i class="fa-solid fa-arrow-right" aria-hidden="true"></i></span>
                    </div>
                </div>
            </a>`;
    }

    // Resim yüklenince yumuşakça belir; bozuksa kaynak adı yazısına dön
    grid.addEventListener('load', e => { if (e.target.tagName === 'IMG') e.target.classList.add('loaded'); }, true);
    grid.addEventListener('error', e => {
        if (e.target.tagName !== 'IMG') return;
        const media = e.target.parentElement;
        const card = media.closest('.news-card');
        const item = allNews.find(h => 'haber.html?id=' + encodeURIComponent(h.id) === card.getAttribute('href'));
        media.innerHTML = `<span>${clean(item ? item.kaynak : '')}</span>`;
    }, true);

    /* ---------- Sayfalama (en fazla ~7 düğme, 1000 sayfada bile) ---------- */
    function pageTokens(total, current, siblings) {
        const t = new Set([1, total, current]);
        for (let d = 1; d <= siblings; d++) { t.add(current - d); t.add(current + d); }
        const nums = Array.from(t).filter(n => n >= 1 && n <= total).sort((a, b) => a - b);
        const out = [];
        nums.forEach((n, i) => {
            if (i > 0) {
                const gap = n - nums[i - 1];
                if (gap === 2) out.push(n - 1);        // tek sayı boşluğu → doğrudan göster
                else if (gap > 2) out.push('gap');
            }
            out.push(n);
        });
        return out;
    }

    const narrow = window.matchMedia('(max-width: 520px)');

    function renderPagination(totalItems) {
        pager.innerHTML = '';
        const total = Math.ceil(totalItems / PER_PAGE);
        if (total <= 1) return;

        const mk = (html, opts = {}) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'page-btn' + (opts.active ? ' active' : '');
            b.innerHTML = html;
            if (opts.label) b.setAttribute('aria-label', opts.label);
            if (opts.active) b.setAttribute('aria-current', 'page');
            b.disabled = !!opts.disabled;
            if (!opts.disabled && !opts.active) b.onclick = () => goTo(opts.to);
            return b;
        };

        pager.appendChild(mk('<i class="fa-solid fa-arrow-left" aria-hidden="true"></i><span class="page-label">Önceki</span>',
            { disabled: page === 1, to: page - 1, label: 'Önceki sayfa' }));

        pageTokens(total, page, narrow.matches ? 0 : 1).forEach(tk => {
            if (tk === 'gap') {
                const s = document.createElement('span');
                s.className = 'page-gap'; s.textContent = '…'; s.setAttribute('aria-hidden', 'true');
                pager.appendChild(s);
            } else {
                pager.appendChild(mk(String(tk), { active: tk === page, to: tk, label: `Sayfa ${tk}` }));
            }
        });

        pager.appendChild(mk('<span class="page-label">Sonraki</span><i class="fa-solid fa-arrow-right" aria-hidden="true"></i>',
            { disabled: page === total, to: page + 1, label: 'Sonraki sayfa' }));
    }
    narrow.addEventListener('change', () => { if (allNews.length) renderPagination(filtered().length); });

    /* ---------- Filtre / render ---------- */
    function filtered() {
        const q = fold(query.trim());
        return allNews.filter(h =>
            (category === 'Tümü' || h.kategori === category) &&
            (!q || h._idx.includes(q)));
    }

    function paint() {
        const list = filtered();
        const totalPages = Math.max(1, Math.ceil(list.length / PER_PAGE));
        if (page > totalPages) page = totalPages;
        const slice = list.slice((page - 1) * PER_PAGE, page * PER_PAGE);

        if (!slice.length) {
            grid.innerHTML = `<div class="state-box glass-card"><h3>Haber bulunamadı</h3><p>Bu kriterlere uygun haber yok. Aramayı ya da kategoriyi değiştirmeyi deneyin.</p></div>`;
            pager.innerHTML = '';
            return;
        }
        grid.innerHTML = slice.map(cardHTML).join('');
        grid.querySelectorAll('img').forEach(img => { if (img.complete && img.naturalWidth) img.classList.add('loaded'); });
        renderPagination(list.length);
    }

    // Eski içerik solar → yenisi sırayla girer. Hızlı tıklamalarda en son istek kazanır.
    function update({ animate = true, scrollTop = false } = {}) {
        const token = ++renderToken;
        saveState();
        if (!animate || !LEAVE_MS) { paint(); return; }

        grid.style.minHeight = grid.offsetHeight + 'px';   // alt kısım (footer) zıplamasın
        grid.classList.add('is-leaving');
        pager.classList.add('is-leaving');
        if (scrollTop) scrollToList();

        setTimeout(() => {
            if (token !== renderToken) return;
            paint();
            grid.classList.remove('is-leaving');
            pager.classList.remove('is-leaving');
            requestAnimationFrame(() => { grid.style.minHeight = ''; });
        }, LEAVE_MS);
    }

    function scrollToList() {
        const top = grid.getBoundingClientRect().top + window.scrollY - (parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h')) || 0) * 16 - 24;
        window.scrollTo({ top: Math.max(0, top), behavior: reducedMotion ? 'auto' : 'smooth' });
    }

    function goTo(p) { page = p; update({ scrollTop: true }); }

    /* ---------- Olaylar ---------- */
    filterBtns.forEach(btn => btn.addEventListener('click', () => {
        if (btn.dataset.category === category) return;
        category = btn.dataset.category;
        page = 1;
        syncFilterUI(true);
        update();
    }));

    let searchTimer;
    searchInput.addEventListener('input', e => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => { query = e.target.value; page = 1; update(); }, 180);
    });

    window.addEventListener('resize', () => syncFilterUI(true));
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => syncFilterUI(true));

    /* ---------- Yükleme ---------- */
    async function load() {
        grid.innerHTML = skeletonCards(6);
        pager.innerHTML = '';
        try {
            const res = await fetch('liste.json');
            if (!res.ok) throw new Error('Liste dosyası bulunamadı.');
            allNews = await res.json();
            allNews.forEach(h => { h._idx = fold(h.baslik + ' ' + h.ozet); });
            totalEl.textContent = `Toplam ${allNews.length} haber listelenmektedir.`;
            paint();
        } catch (err) {
            console.error('Haberler yüklenirken hata:', err);
            grid.innerHTML = `
                <div class="state-box is-error glass-card" role="alert">
                    <h3>Haberler yüklenemedi</h3>
                    <p>Liste henüz oluşmamış olabilir ya da bağlantınızda bir sorun var.</p>
                    <button type="button" class="retry-btn" id="retry-btn">Tekrar dene</button>
                </div>`;
            document.getElementById('retry-btn').onclick = load;
        }
    }

    restoreState();
    // Haber sayfasındaki "Kategoriler" bağlantıları: ./?kategori=Anime
    const urlCat = new URLSearchParams(location.search).get('kategori');
    if (['Anime', 'Çizgi Film'].includes(urlCat)) { category = urlCat; page = 1; query = ''; }
    searchInput.value = query;
    syncFilterUI(false);
    load();
})();
