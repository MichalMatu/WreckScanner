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
        rel = str(photo.get("public_image_file") or photo.get("public_thumb_file") or "")
        if not rel:
            continue
        label = str(photo.get("original_filename") or photo.get("id") or "zdjęcie z miejsca")
        figures.append(_figure(rel, label))
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


def _figure(src: str, caption: str) -> str:
    return f"""
<figure>
  <img src="{html.escape(src, quote=True)}" alt="">
  <figcaption>{html.escape(caption, quote=False)}</figcaption>
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
  @media print {{
    main {{ max-width: none; padding: 14mm; }}
    h1 {{ font-size: 18pt; }}
    h2 {{ font-size: 15pt; }}
    body {{ font-size: 9pt; }}
    img {{ height: 48mm; }}
    .evidence-section--crops img {{ height: 40mm; }}
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
