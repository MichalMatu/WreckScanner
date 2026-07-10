// ─── i18n runtime ─────────────────────────────────
// Słowniki są ładowane przed tym plikiem z /i18n/pl.js i /i18n/en.js.

const I18N_LANG_KEY = 'wroclaw-ortho-lang';

const TRANSLATIONS = {
    pl: TRANSLATIONS_PL,
    en: TRANSLATIONS_EN,
};

// Bieżący język — wybór z localStorage → navigator → 'pl'
function detectLang() {
    const requested = new URLSearchParams(window.location.search).get('lang');
    if (requested === 'pl' || requested === 'en') return requested;
    try {
        const saved = localStorage.getItem(I18N_LANG_KEY);
        if (saved === 'pl' || saved === 'en') return saved;
    } catch (_) {}
    const nav = (navigator.language || navigator.userLanguage || '').toLowerCase();
    return nav.startsWith('pl') ? 'pl' : 'en';
}

let CURRENT_LANG = detectLang();

function t(key, params) {
    const dict = TRANSLATIONS[CURRENT_LANG] || TRANSLATIONS.pl;
    let str = dict[key];
    if (str === undefined) str = TRANSLATIONS.pl[key] || key;
    if (params) {
        for (const k of Object.keys(params)) {
            str = str.replaceAll(`{${k}}`, String(params[k]));
        }
    }
    return str;
}

// Ustaw tekst we wszystkich elementach z data-i18n / data-i18n-attr.
function applyI18n() {
    document.documentElement.lang = CURRENT_LANG;

    // textContent / innerHTML
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        const allowHtml = el.dataset.i18nHtml !== undefined;
        const value = t(key);
        if (allowHtml) {
            el.innerHTML = value;
        } else {
            el.textContent = value;
        }
    });

    // atrybuty: data-i18n-attr="title:icon.settings" lub multiple: "title:x;aria-label:y"
    document.querySelectorAll('[data-i18n-attr]').forEach(el => {
        const spec = el.dataset.i18nAttr;
        spec.split(';').forEach(pair => {
            const [attr, key] = pair.split(':');
            if (attr && key) el.setAttribute(attr.trim(), t(key.trim()));
        });
    });

    // tytuł strony i meta description
    const titleKey = document.documentElement.dataset.i18nTitle || 'meta.title';
    const descriptionKey = document.documentElement.dataset.i18nDescription || 'meta.description';
    document.title = t(titleKey);
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) metaDesc.setAttribute('content', t(descriptionKey));

    // przełącznik języka — zaznacz aktywną opcję
    document.querySelectorAll('[data-lang-option]').forEach(el => {
        el.classList.toggle('active', el.dataset.langOption === CURRENT_LANG);
    });
}

function setLang(lang) {
    if (lang !== 'pl' && lang !== 'en') return;
    CURRENT_LANG = lang;
    try { localStorage.setItem(I18N_LANG_KEY, lang); } catch (_) {}
    applyI18n();
    // Powiadom resztę aplikacji że tekst się zmienił (np. aktywne popupy)
    document.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
}

// Auto-apply on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyI18n);
} else {
    applyI18n();
}
