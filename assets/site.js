/* Kerimu Haber — ortak yardımcılar (üç sayfada da yüklenir) */
(function () {
    'use strict';

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // HTML entity'lerini çöz (RSS başlıklarındaki &amp; &#8217; gibi) — güvenli: textarea kodu çalıştırmaz
    const _ta = document.createElement('textarea');
    function decode(str) {
        _ta.innerHTML = String(str == null ? '' : str);
        return _ta.value;
    }

    // Metni HTML'e güvenle yerleştirmek için kaçışla
    function esc(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    // RSS'ten gelen metin: önce çöz, sonra kaçışla → hem doğru görünür hem güvenli
    function clean(str) { return esc(decode(str)); }

    // Türkçe karakterden bağımsız arama için
    function fold(str) {
        return decode(str).toLocaleLowerCase('tr')
            .replace(/ı/g, 'i').replace(/ş/g, 's').replace(/ç/g, 'c')
            .replace(/ğ/g, 'g').replace(/ö/g, 'o').replace(/ü/g, 'u');
    }

    // alert() yerine
    let toastEl, toastTimer;
    function toast(message) {
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.className = 'toast';
            toastEl.setAttribute('role', 'status');
            toastEl.setAttribute('aria-live', 'polite');
            document.body.appendChild(toastEl);
        }
        toastEl.textContent = message;
        // reflow → animasyon her seferinde çalışsın
        toastEl.classList.remove('show'); void toastEl.offsetWidth;
        toastEl.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2600);
    }

    // <head> meta etiketlerini güncelle (haber sayfası için)
    function setMeta(selector, attr, value) {
        let el = document.head.querySelector(selector);
        if (!el) return;
        el.setAttribute(attr, value);
    }

    function setYear() {
        document.querySelectorAll('[data-year]').forEach(el => { el.textContent = new Date().getFullYear(); });
    }

    window.Kerimu = { reducedMotion, decode, esc, clean, fold, toast, setMeta };
    document.addEventListener('DOMContentLoaded', setYear);
})();
