from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from core import config
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


def _photo_upload_section(wreck_id: str) -> str:
    safe_id = html.escape(wreck_id)
    accept_types = ",".join(sorted(config.ALLOWED_UPLOAD_IMAGE_FORMATS))
    allowed_types = json.dumps(sorted(config.ALLOWED_UPLOAD_IMAGE_FORMATS))
    max_mb = config.MAX_WRECK_PHOTO_BYTES // config.BYTES_PER_MIB
    return f"""
    <section class="evidence photo-upload" data-report-photo-upload>
      <h2>Dodaj zdjęcia do sprawy</h2>
      <form id="wreck-photo-form">
        <input type="file" id="wreck-photo-files" name="photos[]" accept="{accept_types}" multiple required>
        <p>JPG, PNG albo WebP, maks. {max_mb} MB każde, do {config.MAX_WRECK_PHOTOS_PER_UPLOAD} zdjęć naraz.</p>
        <button type="submit">Dodaj zdjęcia</button>
      </form>
      <p id="wreck-photo-status">Zdjęcia dodane publicznie trafią do weryfikacji administratora.</p>
    </section>
    <script data-report-photo-upload-script>
    (() => {{
      const wreckId = {json.dumps(wreck_id)};
      const form = document.getElementById('wreck-photo-form');
      const input = document.getElementById('wreck-photo-files');
      const submit = form?.querySelector('button[type="submit"]');
      const status = document.getElementById('wreck-photo-status');
      const maxBytes = {config.MAX_WRECK_PHOTO_BYTES};
      const maxFiles = {config.MAX_WRECK_PHOTOS_PER_UPLOAD};
      const allowed = new Set({allowed_types});
      form?.addEventListener('submit', async event => {{
        event.preventDefault();
        const files = Array.from(input?.files || []);
        if (!files.length) return;
        if (files.length > maxFiles) {{
          if (status) status.textContent = `Wybierz maksymalnie ${{maxFiles}} zdjęć naraz.`;
          return;
        }}
        for (const file of files) {{
          if (file.size > maxBytes || (file.type && !allowed.has(file.type))) {{
            if (status) status.textContent = 'Dozwolone są tylko zdjęcia JPG, PNG albo WebP do {max_mb} MB.';
            return;
          }}
        }}
        if (status) status.textContent = 'Dodaję zdjęcia...';
        const data = new FormData(form);
        const resp = await fetch(`/api/wrecks/${{encodeURIComponent(wreckId)}}/photos`, {{ method: 'POST', body: data }});
        const payload = await resp.json().catch(() => ({{}}));
        if (!resp.ok || payload.status !== 'ok') {{
          if (status) status.textContent = payload.error || 'Nie udało się dodać zdjęć.';
          return;
        }}
        location.reload();
      }});
    }})();
    </script>
    <!-- Upload endpoint: /api/wrecks/{safe_id}/photos -->
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
        metadata_links = []
        evidence_dir = record_dir / raw_evidence_path
        for file_name in ("candidate.json", "manual_inspection.json", "metadata.json", "links.json"):
            if (evidence_dir / file_name).exists():
                safe_file_name = html.escape(file_name)
                metadata_links.append(f'<a href="{evidence_path}/{safe_file_name}">{safe_file_name}</a>')
        metadata_links_html = f"<p>{' · '.join(metadata_links)}</p>" if metadata_links else ""
        evidence_meta = ["punkt ręczny" if evidence.get("rank") is None else f"Rank #{evidence.get('rank')}"]
        if evidence.get("score") is not None:
            evidence_meta.append(f"score {(float(evidence.get('score') or 0) * 100):.0f}%")
        evidence_meta.append(f"lata: {html.escape(evidence_labels)}")
        evidence_sections.append(
            f"""
            <section class="evidence">
              <h2>Dowód {html.escape(evidence["id"])} · {html.escape(evidence["created_at"])}</h2>
              <p>{" · ".join(evidence_meta)}</p>
              <div class="grid">{"".join(crop_cards)}</div>
              {metadata_links_html}
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
    score = float(record.get("best_score") or 0) * 100
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
    .score {{ color:var(--acc); font-weight:800; }}
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
    .photo-upload form {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; }}
    .photo-upload input {{ max-width:360px; color:var(--mut); }}
    .photo-upload button {{ border:0; border-radius:8px; padding:9px 12px; background:#2563eb; color:white; font-weight:800; cursor:pointer; }}
    .photo-upload p {{ margin:4px 0 0; font-size:12px; }}
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
      <span class="metric"><b>score</b><span class="score">{score:.0f}%</span></span>
      <span class="metric"><b>widziane</b>{html.escape(record_labels)}</span>
      <span class="metric"><b>dowody</b>{evidence_count}</span>
      <span class="metric"><b>zdjęcia</b>{photo_count}</span>
      <span class="metric"><b>ostatni dowód</b>{html.escape(_compact_datetime(latest.get("created_at")))}</span>
    </div>
    <nav class="link-strip">{links_html}</nav>
  </section>
  {_attached_photo_sections(record)}
  {"".join(evidence_sections)}
  {_photo_upload_section(record["id"])}
</main>
</body>
</html>
"""
    (record_dir / "index.html").write_text(html_body, encoding="utf-8")
