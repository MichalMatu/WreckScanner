from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from core import report_models
from core.photo_privacy import is_approved


def _fallback_report_html(record: dict[str, Any]) -> bytes:
    title = f"Teczka pojazdu {record.get('id', '')}"
    labels = ", ".join(str(label) for label in record.get("labels_present") or [])
    body = f"""<!doctype html>
<html lang="pl">
<head><meta charset="utf-8"><title>{html.escape(title)}</title></head>
<body>
<h1>{html.escape(title)}</h1>
<p>{float(record.get("lat") or 0):.6f}, {float(record.get("lon") or 0):.6f}</p>
<p>Widziane: {html.escape(labels or "brak danych")}</p>
</body>
</html>
"""
    return body.encode("utf-8")


def _mail_draft_html_section(recipient: str, subject: str, mail_body: str) -> str:
    return f"""
<section class="evidence report-mail-draft">
<h2>Treść zgłoszenia</h2>
<dl>
<dt>Adresat</dt>
<dd>{html.escape(recipient)}</dd>
<dt>Temat</dt>
<dd>{html.escape(subject)}</dd>
</dl>
<pre>{html.escape(mail_body)}</pre>
</section>
"""


def _report_package_style() -> str:
    return """
<style data-report-package-style>
  .report-mail-draft pre {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;
    max-width: 100%;
    box-sizing: border-box;
  }
  .report-package-photos .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 10px;
  }
  .report-package-photos figure {
    margin: 0;
    border: 1px solid var(--bdr, #1f2937);
    border-radius: 8px;
    overflow: hidden;
    background: #0f172a;
  }
  .report-package-photos img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    display: block;
  }
  .report-package-photos figcaption {
    padding: 8px;
    color: var(--mut, #94a3b8);
    font-size: 12px;
    text-align: center;
    overflow-wrap: anywhere;
  }
</style>
"""


def _strip_interactive_report_controls(html_text: str) -> str:
    html_text = re.sub(
        r"\s*<section class=\"evidence photo-upload\" data-report-photo-upload>.*?</section>",
        "",
        html_text,
        flags=re.DOTALL,
    )
    return re.sub(r"\s*<script data-report-photo-upload-script>.*?</script>", "", html_text, flags=re.DOTALL)


def _inject_report_package_style(html_text: str) -> str:
    if "data-report-package-style" in html_text:
        return html_text
    style = _report_package_style()
    lower_html = html_text.lower()
    idx = lower_html.rfind("</head>")
    if idx != -1:
        return f"{html_text[:idx]}{style}{html_text[idx:]}"
    return f"{style}{html_text}"


def _report_package_photos_section(photos: list[report_models.PreparedReportPhoto]) -> str:
    if not photos:
        return ""
    figures = []
    for photo in photos:
        figures.append(
            f"""
            <figure>
              <img src="zdjecia_z_miejsca/{html.escape(photo.optimized_name)}" loading="lazy" alt="">
              <figcaption>{html.escape(photo.original_name)}</figcaption>
            </figure>
            """
        )
    return f"""
<section class="evidence report-package-photos">
<h2>Zdjęcia dołączone do zgłoszenia</h2>
<div class="grid">{"".join(figures)}</div>
</section>
"""


def build_admin_report_html(
    record_dir: Path,
    record: dict[str, Any],
    recipient: str,
    subject: str,
    mail_body: str,
    photos: list[report_models.PreparedReportPhoto],
) -> bytes:
    report_html = record_dir / "index.html"
    if report_html.exists():
        html_text = report_html.read_text(encoding="utf-8")
    else:
        html_text = _fallback_report_html(record).decode("utf-8")

    html_text = _inject_report_package_style(_strip_interactive_report_controls(html_text))
    section = _report_package_photos_section(photos) + _mail_draft_html_section(recipient, subject, mail_body)
    lower_html = html_text.lower()
    for marker in ("</main>", "</body>"):
        idx = lower_html.rfind(marker)
        if idx != -1:
            html_text = f"{html_text[:idx]}{section}{html_text[idx:]}"
            break
    else:
        html_text = f"{html_text}\n{section}"
    return html_text.encode("utf-8")


def build_public_report_html(
    record: dict[str, Any],
    evidence: dict[str, Any],
    subject: str,
    mail_body: str,
    photos: list[report_models.PreparedReportPhoto],
) -> bytes:
    attached = record.get("attached_photos") if isinstance(record.get("attached_photos"), list) else []
    attached_figures = []
    for photo in attached:
        if not isinstance(photo, dict) or not is_approved(photo):
            continue
        rel = html.escape(str(photo.get("public_image_file") or photo.get("public_thumb_file") or ""))
        if rel:
            attached_figures.append(
                f'<figure><img src="{rel}" alt=""><figcaption>Zdjęcie ze sprawy pojazdu</figcaption></figure>'
            )

    crop_figures = []
    for crop in evidence.get("crops") or []:
        if not isinstance(crop, dict):
            continue
        label = report_models.safe_filename(str(crop.get("label") or "miniatura"), "miniatura", ".jpg")
        crop_figures.append(
            f'<figure><img src="miniatury_historyczne/{html.escape(label)}" alt=""><figcaption>{html.escape(str(crop.get("label") or ""))}</figcaption></figure>'
        )

    user_figures = [
        f'<figure><img src="zdjecia_z_miejsca/{html.escape(photo.optimized_name)}" alt=""><figcaption>{html.escape(photo.original_name)}</figcaption></figure>'
        for photo in photos
    ]
    gallery = "".join(crop_figures + attached_figures + user_figures) or "<p>Brak zdjęć w pakiecie.</p>"
    body = f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>{html.escape(subject)}</title>
<style>
body {{ font-family: system-ui, sans-serif; color: #0f172a; margin: 32px; line-height: 1.55; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
figure {{ margin: 0; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; }}
img {{ width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }}
figcaption {{ padding: 8px; color: #475569; font-size: 12px; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; }}
</style>
</head>
<body>
<h1>{html.escape(subject)}</h1>
<p>Teczka pojazdu: {html.escape(str(record.get("id") or ""))}</p>
<p>Współrzędne: {float(record.get("lat") or 0):.6f}, {float(record.get("lon") or 0):.6f}</p>
<h2>Zdjęcia publiczne i dołączone</h2>
<div class="grid">{gallery}</div>
<h2>Treść zgłoszenia</h2>
<pre>{html.escape(mail_body)}</pre>
</body>
</html>
"""
    return body.encode("utf-8")
