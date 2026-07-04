from __future__ import annotations

REPORT_PACKAGE_STYLE = """
  @page {
    size: A4;
    margin: 14mm;
  }
  :root {
    color-scheme: light;
    --page-bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #0f172a;
    --muted: #475569;
    --border: #cbd5e1;
    --link: #2563eb;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--page-bg);
    color: var(--text);
    font-family: DejaVu Sans, Arial, system-ui, sans-serif;
    font-size: 15px;
    line-height: 1.62;
  }
  main {
    width: min(1080px, calc(100vw - 72px));
    max-width: 1080px;
    margin: 0 auto;
    padding: 46px 0 72px;
  }
  h1 {
    margin: 0 0 6px;
    font-size: 34px;
    line-height: 1.18;
    letter-spacing: 0;
  }
  h2 {
    margin: 34px 0 14px;
    font-size: 27px;
    line-height: 1.2;
    letter-spacing: 0;
  }
  p { margin: 0 0 10px; }
  a { color: var(--link); text-decoration: none; }
  button { font: inherit; }
  .muted { color: var(--muted); }
  .recipient, .subject, .letter-body {
    margin-top: 14px;
  }
  .letter-body {
    width: 100%;
    margin-top: 22px;
    padding: 26px 30px;
    border: 1px solid var(--border);
    background: var(--card-bg);
    white-space: pre-wrap;
    text-wrap: pretty;
    overflow-wrap: break-word;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
  }
  .report-inline-link {
    display: inline-flex;
    max-width: 100%;
    align-items: center;
    padding: 3px 9px;
    border-radius: 999px;
    background: #dbeafe;
    color: #1d4ed8;
    font-weight: 700;
    white-space: normal;
    overflow-wrap: anywhere;
  }
  .evidence-section {
    break-inside: avoid;
    margin-top: 36px;
  }
  .photo-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }
  .evidence-section--crops .photo-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  figure {
    margin: 0;
    padding: 10px;
    background: var(--card-bg);
    border: 1px solid var(--border);
  }
  .report-photo-figure {
    cursor: pointer;
  }
  .report-photo-figure figcaption {
    cursor: pointer;
  }
  .report-photo-link {
    display: block;
    color: inherit;
    cursor: pointer;
  }
  .report-photo-link img {
    cursor: pointer;
    transition: opacity 120ms ease, filter 120ms ease;
  }
  .report-photo-link:hover img,
  .report-photo-link:focus-visible img {
    opacity: 0.88;
    filter: saturate(1.08);
  }
  .report-photo-link:focus-visible {
    outline: 3px solid rgba(37, 99, 235, 0.44);
    outline-offset: 3px;
  }
  img {
    display: block;
    width: 100%;
    height: 180px;
    object-fit: contain;
  }
  .evidence-section--crops img {
    height: 150px;
  }
  figcaption {
    margin-top: 8px;
    color: var(--muted);
    font-size: 12px;
    overflow-wrap: anywhere;
  }
  .empty-evidence { color: var(--muted); }
  .report-lightbox[hidden] {
    display: none;
  }
  .report-lightbox {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: grid;
    place-items: center;
    padding: 24px;
    background: rgba(15, 23, 42, 0.86);
  }
  .report-lightbox-panel {
    position: relative;
    width: min(1120px, 100%);
    max-height: calc(100vh - 48px);
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr) 44px;
    gap: 12px;
    align-items: center;
  }
  .report-lightbox-figure {
    min-width: 0;
    margin: 0;
    padding: 0;
    border: 0;
    background: transparent;
  }
  .report-lightbox-image {
    width: 100%;
    max-height: calc(100vh - 132px);
    height: auto;
    object-fit: contain;
    background: #020617;
  }
  .report-lightbox-caption {
    margin-top: 10px;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: #e2e8f0;
    font-size: 12px;
  }
  .report-lightbox-close,
  .report-lightbox-nav {
    border: 1px solid rgba(226, 232, 240, 0.28);
    background: rgba(15, 23, 42, 0.82);
    color: #fff;
    cursor: pointer;
  }
  .report-lightbox-close {
    position: absolute;
    top: -2px;
    right: 56px;
    z-index: 1;
    min-height: 36px;
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 700;
  }
  .report-lightbox-nav {
    width: 44px;
    height: 44px;
    border-radius: 999px;
    font-size: 26px;
    line-height: 1;
  }
  .report-lightbox-nav:disabled {
    opacity: 0.36;
    cursor: default;
  }
  @media print {
    main { width: auto; max-width: none; padding: 14mm; }
    h1 { font-size: 18pt; }
    h2 { font-size: 15pt; }
    body { font-size: 9pt; }
    .letter-body {
      max-width: none;
      padding: 0;
      border: 0;
      box-shadow: none;
      background: transparent;
    }
    .report-inline-link {
      display: inline;
      padding: 0;
      border-radius: 0;
      background: transparent;
      color: var(--link);
      font-weight: inherit;
    }
    img { height: 48mm; }
    .evidence-section--crops img { height: 40mm; }
    .report-photo-figure,
    .report-photo-figure figcaption,
    .report-photo-link,
    .report-photo-link img { cursor: default; }
    .report-lightbox { display: none !important; }
  }
  @media (max-width: 640px) {
    main {
      width: min(100% - 24px, 1080px);
      padding: 24px 0 44px;
    }
    h1 {
      font-size: 27px;
    }
    .letter-body {
      padding: 18px;
    }
    .report-lightbox {
      padding: 12px;
    }
    .report-lightbox-panel {
      grid-template-columns: 36px minmax(0, 1fr) 36px;
      gap: 8px;
      max-height: calc(100vh - 24px);
    }
    .report-lightbox-nav {
      width: 36px;
      height: 36px;
    }
    .report-lightbox-close {
      right: 44px;
    }
  }
""".strip()


REPORT_LIGHTBOX_HTML = """
<div class="report-lightbox" id="report-lightbox" role="dialog" aria-modal="true" aria-label="Podgląd zdjęcia" hidden>
  <div class="report-lightbox-panel">
    <button type="button" class="report-lightbox-close" data-report-gallery-close>Wróć</button>
    <button type="button" class="report-lightbox-nav" data-report-gallery-prev aria-label="Poprzednie zdjęcie">‹</button>
    <figure class="report-lightbox-figure">
      <img class="report-lightbox-image" id="report-lightbox-image" alt="">
      <figcaption class="report-lightbox-caption">
        <span id="report-lightbox-caption"></span>
        <span id="report-lightbox-counter"></span>
      </figcaption>
    </figure>
    <button type="button" class="report-lightbox-nav" data-report-gallery-next aria-label="Następne zdjęcie">›</button>
  </div>
</div>
""".strip()


REPORT_GALLERY_SCRIPT = """
(() => {
  const links = Array.from(document.querySelectorAll('[data-report-gallery-item]'));
  const lightbox = document.getElementById('report-lightbox');
  const image = document.getElementById('report-lightbox-image');
  const caption = document.getElementById('report-lightbox-caption');
  const counter = document.getElementById('report-lightbox-counter');
  const closeButton = document.querySelector('[data-report-gallery-close]');
  const prevButton = document.querySelector('[data-report-gallery-prev]');
  const nextButton = document.querySelector('[data-report-gallery-next]');
  if (!links.length || !lightbox || !image || !caption || !counter) return;

  const items = links.map((link) => ({
    src: link.getAttribute('href') || '',
    caption: link.dataset.caption || '',
  })).filter((item) => item.src);
  let index = 0;
  let lastFocus = null;

  function render() {
    const item = items[index];
    if (!item) return;
    image.src = item.src;
    image.alt = item.caption || 'Zdjęcie';
    caption.textContent = item.caption || '';
    counter.textContent = items.length > 1 ? `${index + 1}/${items.length}` : '';
    if (prevButton) prevButton.disabled = items.length <= 1;
    if (nextButton) nextButton.disabled = items.length <= 1;
  }

  function open(nextIndex, trigger) {
    index = Math.max(0, Math.min(nextIndex, items.length - 1));
    lastFocus = trigger || document.activeElement;
    render();
    lightbox.hidden = false;
    closeButton?.focus();
  }

  function close() {
    lightbox.hidden = true;
    image.removeAttribute('src');
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
  }

  function move(delta) {
    if (items.length <= 1) return;
    index = (index + delta + items.length) % items.length;
    render();
  }

  links.forEach((link, linkIndex) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      open(linkIndex, link);
    });
  });

  closeButton?.addEventListener('click', close);
  prevButton?.addEventListener('click', () => move(-1));
  nextButton?.addEventListener('click', () => move(1));
  lightbox.addEventListener('click', (event) => {
    if (event.target === lightbox) close();
  });
  document.addEventListener('keydown', (event) => {
    if (lightbox.hidden) return;
    if (event.key === 'Escape') close();
    if (event.key === 'ArrowLeft') move(-1);
    if (event.key === 'ArrowRight') move(1);
  });
})();
""".strip()
