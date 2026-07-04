from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core import config, report_models
from core.photo_privacy import is_approved
from core.report_templates import REPORT_GALLERY_SCRIPT, REPORT_LIGHTBOX_HTML, REPORT_PACKAGE_STYLE

URL_RE = re.compile(r"https?://[^\s<]+")


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


def _linkify_urls(value: Any) -> str:
    text = str(value or "")
    parts: list[str] = []
    last = 0
    for match in URL_RE.finditer(text):
        raw_url = match.group(0)
        parts.append(html.escape(text[last : match.start()], quote=False))
        escaped_href = html.escape(raw_url, quote=True)
        escaped_label = html.escape(_url_label(raw_url), quote=False)
        parts.append(
            f'<a class="report-inline-link" href="{escaped_href}" target="_blank" rel="noopener" '
            f'title="{escaped_href}">{escaped_label}</a>'
        )
        last = match.end()
    parts.append(html.escape(text[last:], quote=False))
    return "".join(parts)


def _url_label(raw_url: str) -> str:
    if "photo=" in raw_url and ("lat=" in raw_url or "lon=" in raw_url):
        return "Otwórz miejsce w WreckScanner"
    return raw_url


def _text_block(value: str) -> str:
    return _linkify_urls(value)


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
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Zgłoszenie dotyczące pojazdu nieużytkowanego</title>
<style data-report-package-style>
{REPORT_PACKAGE_STYLE}
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
{REPORT_LIGHTBOX_HTML}
<script data-report-gallery-script>
{REPORT_GALLERY_SCRIPT}
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
