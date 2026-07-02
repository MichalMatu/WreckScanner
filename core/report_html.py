from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any

from core import config, report_models
from core.photo_privacy import is_approved


def _report_datetime_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "brak danych"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text.replace("T", " ").removesuffix("Z")
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone()
    return parsed.strftime("%d.%m.%Y, godz. %H:%M")


def _recipient_lines(recipient: str) -> list[str]:
    if recipient == config.REPORT_RECIPIENT:
        return [
            "Adresat:",
            "Straż Miejska Wrocławia",
            "ul. Na Grobli 14/16, 50-421 Wrocław",
            recipient,
        ]
    return ["Adresat:", recipient]


def _text_block(value: str) -> str:
    return html.escape(str(value or ""), quote=False)


def _line_block(lines: list[str]) -> str:
    escaped = [html.escape(line, quote=False) for line in lines]
    if escaped:
        email = escaped[-1]
        escaped[-1] = f'<a href="mailto:{email}">{email}</a>'
    return "<br>".join(escaped)


def _attached_photo_figures(record: dict[str, Any]) -> list[str]:
    photos = record.get("attached_photos") if isinstance(record.get("attached_photos"), list) else []
    figures: list[str] = []
    for photo in photos:
        if not isinstance(photo, dict) or not is_approved(photo):
            continue
        full_rel = str(photo.get("public_image_file") or "")
        thumb_rel = str(photo.get("public_thumb_file") or "")
        if not full_rel and not thumb_rel:
            continue
        label = str(photo.get("original_filename") or photo.get("id") or "zdjęcie z miejsca")
        figures.append(_figure(full_rel or thumb_rel, label, preview_src=thumb_rel or full_rel))
    return figures


def _evidence_figures(evidence: dict[str, Any]) -> list[str]:
    figures: list[str] = []
    for crop in evidence.get("crops") or []:
        if not isinstance(crop, dict):
            continue
        label = str(crop.get("label") or "miniatura")
        filename = report_models.safe_filename(label, "miniatura", ".jpg")
        figures.append(_figure(f"miniatury_historyczne/{filename}", label))
    return figures


def _figure(src: str, caption: str, *, preview_src: str | None = None) -> str:
    escaped_src = html.escape(src, quote=True)
    escaped_preview = html.escape(preview_src or src, quote=True)
    escaped_caption = html.escape(caption, quote=False)
    escaped_title = html.escape(caption or "Otwórz zdjęcie", quote=True)
    return f"""
<figure class="report-photo-figure">
  <a class="report-photo-link" href="{escaped_src}" data-report-gallery-item data-caption="{escaped_title}">
    <img src="{escaped_preview}" alt="">
  </a>
  <figcaption>{escaped_caption}</figcaption>
</figure>
"""


def _photo_section(title: str, figures: list[str], *, variant: str) -> str:
    if not figures:
        return ""
    return f"""
<section class="evidence-section evidence-section--{html.escape(variant, quote=True)}">
  <h2>{html.escape(title, quote=False)}</h2>
  <div class="photo-grid">{"".join(figures)}</div>
</section>
"""


def build_report_html(
    *,
    record: dict[str, Any],
    evidence: dict[str, Any],
    recipient: str,
    subject: str,
    mail_body: str,
) -> bytes:
    report_date = _report_datetime_text(evidence.get("created_at"))
    attached = _attached_photo_figures(record)
    crops = _evidence_figures(evidence)
    evidence_sections = "\n".join(
        section
        for section in (
            _photo_section("Zdjęcia z miejsca", attached, variant="photos"),
            _photo_section("Miniatury historyczne", crops, variant="crops"),
        )
        if section
    )
    if not evidence_sections:
        evidence_sections = '<p class="empty-evidence">Brak zdjęć w pakiecie.</p>'

    body = f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>Zgłoszenie dotyczące pojazdu nieużytkowanego</title>
<style data-report-package-style>
  :root {{
    color-scheme: light;
    --page-bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #0f172a;
    --muted: #475569;
    --border: #cbd5e1;
    --link: #2563eb;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--page-bg);
    color: var(--text);
    font-family: DejaVu Sans, Arial, system-ui, sans-serif;
    font-size: 13px;
    line-height: 1.45;
  }}
  main {{
    max-width: 760px;
    margin: 0 auto;
    padding: 34px 38px 56px;
  }}
  h1 {{
    margin: 0 0 6px;
    font-size: 29px;
    line-height: 1.18;
    letter-spacing: 0;
  }}
  h2 {{
    margin: 26px 0 12px;
    font-size: 24px;
    line-height: 1.2;
    letter-spacing: 0;
  }}
  p {{ margin: 0 0 10px; }}
  a {{ color: var(--link); text-decoration: none; }}
  button {{ font: inherit; }}
  .muted {{ color: var(--muted); }}
  .recipient, .subject, .letter-body {{
    margin-top: 12px;
  }}
  .letter-body {{
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }}
  .evidence-section {{
    break-inside: avoid;
    margin-top: 28px;
  }}
  .photo-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }}
  .evidence-section--crops .photo-grid {{
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }}
  figure {{
    margin: 0;
    padding: 10px;
    background: var(--card-bg);
    border: 1px solid var(--border);
  }}
  .report-photo-figure {{
    cursor: pointer;
  }}
  .report-photo-figure figcaption {{
    cursor: pointer;
  }}
  .report-photo-link {{
    display: block;
    color: inherit;
    cursor: pointer;
  }}
  .report-photo-link img {{
    cursor: pointer;
    transition: opacity 120ms ease, filter 120ms ease;
  }}
  .report-photo-link:hover img,
  .report-photo-link:focus-visible img {{
    opacity: 0.88;
    filter: saturate(1.08);
  }}
  .report-photo-link:focus-visible {{
    outline: 3px solid rgba(37, 99, 235, 0.44);
    outline-offset: 3px;
  }}
  img {{
    display: block;
    width: 100%;
    height: 180px;
    object-fit: contain;
  }}
  .evidence-section--crops img {{
    height: 150px;
  }}
  figcaption {{
    margin-top: 8px;
    color: var(--muted);
    font-size: 12px;
    overflow-wrap: anywhere;
  }}
  .empty-evidence {{ color: var(--muted); }}
  .report-lightbox[hidden] {{
    display: none;
  }}
  .report-lightbox {{
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: grid;
    place-items: center;
    padding: 24px;
    background: rgba(15, 23, 42, 0.86);
  }}
  .report-lightbox-panel {{
    position: relative;
    width: min(1120px, 100%);
    max-height: calc(100vh - 48px);
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr) 44px;
    gap: 12px;
    align-items: center;
  }}
  .report-lightbox-figure {{
    min-width: 0;
    margin: 0;
    padding: 0;
    border: 0;
    background: transparent;
  }}
  .report-lightbox-image {{
    width: 100%;
    max-height: calc(100vh - 132px);
    height: auto;
    object-fit: contain;
    background: #020617;
  }}
  .report-lightbox-caption {{
    margin-top: 10px;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: #e2e8f0;
    font-size: 12px;
  }}
  .report-lightbox-close,
  .report-lightbox-nav {{
    border: 1px solid rgba(226, 232, 240, 0.28);
    background: rgba(15, 23, 42, 0.82);
    color: #fff;
    cursor: pointer;
  }}
  .report-lightbox-close {{
    position: absolute;
    top: -2px;
    right: 56px;
    z-index: 1;
    min-height: 36px;
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 700;
  }}
  .report-lightbox-nav {{
    width: 44px;
    height: 44px;
    border-radius: 999px;
    font-size: 26px;
    line-height: 1;
  }}
  .report-lightbox-nav:disabled {{
    opacity: 0.36;
    cursor: default;
  }}
  @media print {{
    main {{ max-width: none; padding: 14mm; }}
    h1 {{ font-size: 18pt; }}
    h2 {{ font-size: 15pt; }}
    body {{ font-size: 9pt; }}
    img {{ height: 48mm; }}
    .evidence-section--crops img {{ height: 40mm; }}
    .report-photo-figure,
    .report-photo-figure figcaption,
    .report-photo-link,
    .report-photo-link img {{ cursor: default; }}
    .report-lightbox {{ display: none !important; }}
  }}
  @media (max-width: 640px) {{
    .report-lightbox {{
      padding: 12px;
    }}
    .report-lightbox-panel {{
      grid-template-columns: 36px minmax(0, 1fr) 36px;
      gap: 8px;
      max-height: calc(100vh - 24px);
    }}
    .report-lightbox-nav {{
      width: 36px;
      height: 36px;
    }}
    .report-lightbox-close {{
      right: 44px;
    }}
  }}
</style>
</head>
<body>
<main>
  <h1>Zgłoszenie dotyczące pojazdu nieużytkowanego</h1>
  <p class="muted">Data zgłoszenia: {html.escape(report_date, quote=False)}</p>
  <p class="recipient">{_line_block(_recipient_lines(recipient))}</p>
  <p class="subject"><strong>Dotyczy:</strong> {html.escape(subject, quote=False)}</p>
  <div class="letter-body">{_text_block(mail_body)}</div>
  {evidence_sections}
</main>
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
<script data-report-gallery-script>
(() => {{
  const links = Array.from(document.querySelectorAll('[data-report-gallery-item]'));
  const lightbox = document.getElementById('report-lightbox');
  const image = document.getElementById('report-lightbox-image');
  const caption = document.getElementById('report-lightbox-caption');
  const counter = document.getElementById('report-lightbox-counter');
  const closeButton = document.querySelector('[data-report-gallery-close]');
  const prevButton = document.querySelector('[data-report-gallery-prev]');
  const nextButton = document.querySelector('[data-report-gallery-next]');
  if (!links.length || !lightbox || !image || !caption || !counter) return;

  const items = links.map((link) => ({{
    src: link.getAttribute('href') || '',
    caption: link.dataset.caption || '',
  }})).filter((item) => item.src);
  let index = 0;
  let lastFocus = null;

  function render() {{
    const item = items[index];
    if (!item) return;
    image.src = item.src;
    image.alt = item.caption || 'Zdjęcie';
    caption.textContent = item.caption || '';
    counter.textContent = items.length > 1 ? `${{index + 1}}/${{items.length}}` : '';
    if (prevButton) prevButton.disabled = items.length <= 1;
    if (nextButton) nextButton.disabled = items.length <= 1;
  }}

  function open(nextIndex, trigger) {{
    index = Math.max(0, Math.min(nextIndex, items.length - 1));
    lastFocus = trigger || document.activeElement;
    render();
    lightbox.hidden = false;
    closeButton?.focus();
  }}

  function close() {{
    lightbox.hidden = true;
    image.removeAttribute('src');
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
  }}

  function move(delta) {{
    if (items.length <= 1) return;
    index = (index + delta + items.length) % items.length;
    render();
  }}

  links.forEach((link, linkIndex) => {{
    link.addEventListener('click', (event) => {{
      event.preventDefault();
      open(linkIndex, link);
    }});
  }});

  closeButton?.addEventListener('click', close);
  prevButton?.addEventListener('click', () => move(-1));
  nextButton?.addEventListener('click', () => move(1));
  lightbox.addEventListener('click', (event) => {{
    if (event.target === lightbox) close();
  }});
  document.addEventListener('keydown', (event) => {{
    if (lightbox.hidden) return;
    if (event.key === 'Escape') close();
    if (event.key === 'ArrowLeft') move(-1);
    if (event.key === 'ArrowRight') move(1);
  }});
}})();
</script>
</body>
</html>
"""
    return body.encode("utf-8")


def build_admin_report_html(
    _record_dir: Path,
    record: dict[str, Any],
    evidence: dict[str, Any],
    recipient: str,
    subject: str,
    mail_body: str,
) -> bytes:
    return build_report_html(
        record=record,
        evidence=evidence,
        recipient=recipient,
        subject=subject,
        mail_body=mail_body,
    )


def build_public_report_html(
    record: dict[str, Any],
    evidence: dict[str, Any],
    subject: str,
    mail_body: str,
) -> bytes:
    return build_report_html(
        record=record,
        evidence=evidence,
        recipient=config.REPORT_RECIPIENT,
        subject=subject,
        mail_body=mail_body,
    )
