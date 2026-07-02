from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from core.photo_privacy import is_approved


def approved_attached_photos(record: dict[str, Any]) -> list[dict[str, Any]]:
    photos = record.get("attached_photos") if isinstance(record.get("attached_photos"), list) else []
    return [photo for photo in photos if isinstance(photo, dict) and is_approved(photo)]


def _compact_years(labels: list[Any]) -> str:
    years = sorted(int(label) for label in labels if str(label).isdigit())
    if not years:
        return "brak danych"
    if len(years) >= 3:
        return f"{years[0]}-{years[-1]} ({len(years)} lat)"
    return ", ".join(str(year) for year in years)


def _compact_datetime(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "brak danych"
    return text.replace("T", " ").removesuffix("Z")


def _attached_photo_sections(record: dict[str, Any]) -> str:
    photos = approved_attached_photos(record)
    if not photos:
        return ""
    cards: list[str] = []
    for photo in photos:
        public_image = html.escape(str(photo.get("public_image_file") or ""))
        public_thumb = html.escape(str(photo.get("public_thumb_file") or photo.get("public_image_file") or ""))
        if not public_image or not public_thumb:
            continue
        name = html.escape(str(photo.get("original_filename") or "zdjęcie"))
        created_at = html.escape(_compact_datetime(photo.get("captured_at") or photo.get("created_at")))
        cards.append(
            f"""
            <figure class="photo-card">
              <a href="{public_image}" target="_blank" rel="noopener"><img src="{public_thumb}" loading="lazy" alt=""></a>
              <figcaption>{name}<span>{created_at}</span><a href="{public_image}" download>Pobierz zdjęcie</a></figcaption>
            </figure>
            """
        )
    if not cards:
        return ""
    return f"""
    <section class="evidence attached-photos" id="zdjecia-z-miejsca">
      <h2>Zdjęcia z miejsca</h2>
      <div class="grid photo-grid">{"".join(cards)}</div>
    </section>
    """


def render_record_html(record: dict[str, Any], record_dir: Path) -> None:
    title = f"Sprawa pojazdu {record['id']}"
    latest = record.get("latest_evidence") or {}
    attached_photos = approved_attached_photos(record)
    evidence_sections: list[str] = []
    for evidence in reversed(record.get("evidences") or []):
        crop_cards: list[str] = []
        raw_evidence_path = str(evidence["path"])
        evidence_path = html.escape(raw_evidence_path)
        evidence_labels = ", ".join(str(label) for label in evidence.get("labels_present") or [])
        for crop in evidence.get("crops") or []:
            label = html.escape(str(crop.get("label", "")))
            file_name = html.escape(str(crop.get("file", "")))
            crop_cards.append(
                f'<figure><img src="{evidence_path}/{file_name}" loading="lazy"><figcaption>{label}</figcaption></figure>'
            )
        evidence_meta = [f"lata: {html.escape(evidence_labels or 'brak danych')}"]
        evidence_sections.append(
            f"""
            <section class="evidence">
              <h2>Dowód {html.escape(evidence["id"])} · {html.escape(evidence["created_at"])}</h2>
              <p>{" · ".join(evidence_meta)}</p>
              <div class="grid">{"".join(crop_cards)}</div>
            </section>
            """
        )

    links = record.get("links") or {}
    links_html = " · ".join(
        f'<a href="{html.escape(str(url))}" target="_blank" rel="noopener">{html.escape(name.replace("_", " "))}</a>'
        for name, url in links.items()
    )
    record_labels = _compact_years(record.get("labels_present") or [])
    status = html.escape(str(record.get("status", "confirmed")))
    evidence_count = len(record.get("evidences") or [])
    photo_count = len(attached_photos)
    html_body = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0b0f19; --card:#111827; --bdr:#1f2937; --txt:#e5e7eb; --mut:#94a3b8; --acc:#10b981; }}
    body {{ margin:0; background:var(--bg); color:var(--txt); font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ max-width:1280px; margin:0 auto; padding:28px; }}
    .hero,.evidence {{ background:var(--card); border:1px solid var(--bdr); border-radius:12px; padding:18px; margin-bottom:18px; }}
    h1,h2 {{ margin:0 0 10px; }}
    p {{ color:var(--mut); line-height:1.5; overflow-wrap:anywhere; }}
    a {{ color:#93c5fd; text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .hero {{ padding:14px 16px; }}
    .hero-head {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px; }}
    .hero h1 {{ font-size:clamp(20px,3vw,30px); margin:0; overflow-wrap:anywhere; }}
    .status-pill {{ border:1px solid rgba(16,185,129,.35); border-radius:999px; padding:4px 9px; color:#bbf7d0; background:rgba(16,185,129,.08); font-size:12px; font-weight:800; white-space:nowrap; }}
    .metric-strip {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 8px; }}
    .metric {{ border:1px solid rgba(148,163,184,.16); border-radius:999px; padding:5px 9px; background:#0f172a; color:#cbd5e1; font-size:12px; line-height:1.2; }}
    .metric b {{ color:#94a3b8; font-weight:700; margin-right:4px; }}
    .link-strip {{ display:flex; flex-wrap:wrap; gap:6px 10px; font-size:12px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; }}
    figure {{ margin:0; border:1px solid var(--bdr); border-radius:8px; overflow:hidden; background:#0f172a; }}
    img {{ width:100%; aspect-ratio:1; object-fit:cover; display:block; }}
    figcaption {{ padding:8px; color:var(--mut); font-size:12px; text-align:center; }}
    figcaption span {{ display:block; margin-top:3px; color:#64748b; font-size:11px; }}
    .photo-grid {{ grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); }}
    .report-mail-draft pre {{ white-space:pre-wrap; overflow-wrap:anywhere; word-break:break-word; max-width:100%; box-sizing:border-box; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div class="hero-head">
      <h1>{html.escape(title)}</h1>
      <span class="status-pill">{status}</span>
    </div>
    <div class="metric-strip">
      <span class="metric"><b>GPS</b>{record["lat"]:.6f}, {record["lon"]:.6f}</span>
      <span class="metric"><b>widziane</b>{html.escape(record_labels)}</span>
      <span class="metric"><b>dowody</b>{evidence_count}</span>
      <span class="metric"><b>zdjęcia</b>{photo_count}</span>
      <span class="metric"><b>ostatni dowód</b>{html.escape(_compact_datetime(latest.get("created_at")))}</span>
    </div>
    <nav class="link-strip">{links_html}</nav>
  </section>
  {_attached_photo_sections(record)}
  {"".join(evidence_sections)}
</main>
</body>
</html>
"""
    (record_dir / "index.html").write_text(html_body, encoding="utf-8")
