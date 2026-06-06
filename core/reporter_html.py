from __future__ import annotations

import html as html_lib
import json
from pathlib import Path
from typing import Any

from core.geo import external_map_links, google_maps_embed_url
from core.models import Candidate, ImageItem, Observation

REPORT_I18N: dict[str, dict[str, str]] = {
    "pl": {
        "title": "Analiza pojazdów do weryfikacji",
        "legend.title": "Mapa obecnych detekcji",
        "legend.note": "Score to heurystyka rankingowa (pokrycie · kolor · rozpiętość). Wysoka wartość = wysoka pozycja na liście, <b>nie</b> potwierdzenie, że pojazd jest nieużytkowany — to wymaga inspekcji manualnej.",
        "legend.diagnostics": "diagnostyka JSON",
        "legend.cropManifest": "kadrowanie JSON",
        "noCars": "Brak pojazdów na najnowszym zdjęciu.",
        "jumpTo": "Skocz do #{n}",
        "showOnMap": "📍 pokaż na mapie",
        "showOnMap.title": "Pokaż tego kandydata na mapie u góry",
        "saveWreck": "Dodaj pojazd",
        "savingWreck": "Zapisuję...",
        "savedWreck": "Pojazd dodany",
        "alreadySavedWreck": "Już zapisany",
        "saveWreckError": "Błąd zapisu pojazdu",
        "saveWreckDisabled": "Dodawanie pinezek z YOLO jest teraz wyłączone.",
        "score.tooltip": "Heurystyka rankingowa łącząca pokrycie, spójność koloru i rozpiętość czasową. Służy do ułożenia listy — nie potwierdza długiego stania.",
        "badge.coverage": "obecne na {n}/{total} wiarygodnych zdjęciach",
        "badge.color": "spójność koloru {pct}%",
        "badge.yolo": "YOLO teraz {val}",
        "badge.span": "rozpiętość {pct}%",
        "candMeta": "Widziane w: {labels} · braki: {missing} · pominięte kadry: {ignored}",
        "cell.match": "trafienie {conf}",
        "cell.skipped": "pominięte",
        "cell.missing": "brak",
        "cell.empty": "brak",
        "cell.satellite": "Satelita",
        "cell.googleAge": "Google · ?",
        "link.streetView": "Street View",
        "link.gmapsSat": "Google Maps satelita",
        "link.appleMaps": "Apple Maps",
        "link.mapillary": "Mapillary",
        "link.geoportal": "Geoportal Krajowy",
    },
    "en": {
        "title": "Vehicles for verification analysis",
        "legend.title": "Map of current detections",
        "legend.note": "Score is a ranking heuristic (coverage · color · span). High value = high position on the list, <b>not</b> confirmation that the vehicle is unused — manual inspection required.",
        "legend.diagnostics": "diagnostics JSON",
        "legend.cropManifest": "crop manifest JSON",
        "noCars": "No vehicles on the latest image.",
        "jumpTo": "Jump to #{n}",
        "showOnMap": "📍 show on map",
        "showOnMap.title": "Show this candidate on the map above",
        "saveWreck": "Add vehicle",
        "savingWreck": "Saving...",
        "savedWreck": "Vehicle added",
        "alreadySavedWreck": "Already saved",
        "saveWreckError": "Vehicle save failed",
        "saveWreckDisabled": "Saving YOLO vehicle pins is currently disabled.",
        "score.tooltip": "Ranking heuristic combining coverage, color consistency and temporal span. Used to order the list — does not confirm long-term parking.",
        "badge.coverage": "present in {n}/{total} reliable images",
        "badge.color": "color consistency {pct}%",
        "badge.yolo": "YOLO now {val}",
        "badge.span": "span {pct}%",
        "candMeta": "Seen in: {labels} · missing: {missing} · skipped frames: {ignored}",
        "cell.match": "match {conf}",
        "cell.skipped": "skipped",
        "cell.missing": "missing",
        "cell.empty": "missing",
        "cell.satellite": "Satellite",
        "cell.googleAge": "Google · ?",
        "link.streetView": "Street View",
        "link.gmapsSat": "Google Maps satellite",
        "link.appleMaps": "Apple Maps",
        "link.mapillary": "Mapillary",
        "link.geoportal": "Polish Geoportal",
    },
}


def tr(lang: str, key: str, **kwargs: Any) -> str:
    dict_lang = REPORT_I18N.get(lang) or REPORT_I18N["pl"]
    value = dict_lang.get(key) or REPORT_I18N["pl"].get(key) or key
    if kwargs:
        for key_name, replacement in kwargs.items():
            value = value.replace("{" + key_name + "}", str(replacement))
    return value


def versioned_asset_url(path: str, asset_version: str) -> str:
    separator = "&" if "?" in path else "?"
    return html_lib.escape(f"{path}{separator}v={asset_version}", quote=True)


REPORT_CSS = """<style>
  :root { --bg:#0b0f19; --card:#111827; --bdr:#1f2937; --txt:#e5e7eb; --mut:#94a3b8; --acc:#6366f1; --ok:#10b981; --miss:#ef4444; --skip:#64748b; }
  body { font-family:system-ui,sans-serif; background:var(--bg); color:var(--txt); margin:0; padding:24px; }
  .cand { background:var(--card); border:1px solid var(--bdr); border-radius:14px; padding:16px; margin-bottom:18px; }
  .cand-head { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:6px; }
  .rank { font-size:18px; font-weight:700; color:var(--acc); }
  .score b { color:var(--ok); font-size:18px; }
  .badge { font-size:11px; padding:3px 8px; border-radius:8px; background:#1e293b; color:var(--mut); }
  .badge.cov { background:#1e3a8a; color:#bfdbfe; }
  .badge.col { background:#581c87; color:#e9d5ff; }
  .badge.span { background:#064e3b; color:#bbf7d0; }
  .coords { font-size:12px; margin:6px 0 12px; color:var(--mut); }
  .coords a { color:#93c5fd; text-decoration:none; }
  .grid-wrap { display:flex; gap:8px; }
  .crop-cell { display:flex; flex-direction:column; gap:4px; flex:1 1 0; min-width:0; }
  .crop-cell .yr { font-size:11px; color:var(--mut); text-align:center; display:flex; flex-direction:column; gap:2px; }
  .crop-cell .yr span { font-size:10px; color:#cbd5e1; }
  .crop { position:relative; width:100%; aspect-ratio:1/1; background:#0a0f1c; border:1px solid var(--bdr); border-radius:8px; overflow:hidden; }
  .crop img { width:100%; height:100%; object-fit:cover; display:block; }
  .crop iframe { width:100%; height:100%; border:0; display:block; }
  .crop.sat { border-color:#3b82f6; }
  .crop.center::after { content:''; position:absolute; left:50%; top:50%; width:34px; height:34px; transform:translate(-50%,-50%); border:2px solid #f59e0b; border-radius:50%; pointer-events:none; box-shadow:0 0 0 1px rgba(0,0,0,0.5); }
  .crop.present { border-color:var(--ok); }
  .crop.present::after { border-color:var(--ok); }
  .crop.missing { border-color:var(--miss); opacity:.72; }
  .crop.missing::after { border-color:var(--miss); }
  .crop.ignored { border-color:var(--skip); opacity:.58; }
  .crop.ignored::after { border-color:var(--skip); }
  .legend { background:#0d1424; border:1px solid var(--bdr); border-radius:10px; padding:10px 14px; margin-bottom:18px; font-size:13px; color:var(--mut); }
  .legend a { color:#93c5fd; text-decoration:none; }
  .legend a:hover { text-decoration:underline; }
  .score { cursor:help; }
  .locate { font-size:11px; color:#fbbf24; cursor:pointer; text-decoration:none; padding:3px 8px; border:1px solid rgba(251,191,36,0.35); border-radius:8px; background:rgba(251,191,36,0.06); transition:all 0.15s; }
  .locate:hover { background:rgba(251,191,36,0.18); color:#fff; }
  .save-wreck { font-size:11px; color:#bbf7d0; cursor:pointer; padding:4px 9px; border:1px solid rgba(16,185,129,0.35); border-radius:8px; background:rgba(16,185,129,0.10); font-weight:700; }
  .save-wreck:hover { background:rgba(16,185,129,0.22); color:#fff; }
  .save-wreck:disabled { cursor:default; opacity:.78; }
  .overlay-wrap { position:relative; }
  .overlay-pin { position:absolute; width:26px; height:26px; transform:translate(-50%, -50%); border:2px solid #fff; border-radius:50%; cursor:pointer; color:#0b0f19; font-weight:800; font-size:12px; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 6px rgba(0,0,0,0.55); transition:transform 0.15s, box-shadow 0.15s; scroll-margin-top:25vh; line-height:1; }
  .overlay-pin:hover { transform:translate(-50%, -50%) scale(1.18); box-shadow:0 3px 10px rgba(0,0,0,0.7); }
  .overlay-pin.active { animation:pin-pulse 1.2s ease-in-out infinite; box-shadow:0 0 0 4px rgba(251,191,36,0.55), 0 0 18px rgba(251,191,36,0.85); border-color:#fbbf24; }
  .rank { scroll-margin-top:25vh; }
  @keyframes pin-pulse {
    0%, 100% { transform:translate(-50%, -50%) scale(1); }
    50%      { transform:translate(-50%, -50%) scale(1.18); }
  }
</style>"""

REPORT_SCRIPT_TEMPLATE = """<script>
function showOn(n) {
    document.querySelectorAll('.overlay-pin.active').forEach(p => p.classList.remove('active'));
    const pin = document.getElementById('overlay-pin-' + n);
    if (!pin) return;
    pin.classList.add('active');
    pin.scrollIntoView({behavior:'smooth', block:'start'});
}
function goToCand(n) {
    const card = document.getElementById('cand-' + n);
    if (card) card.scrollIntoView({behavior:'smooth', block:'start'});
}
let yoloWreckSavingAllowed = true;
let reportAdminAuthenticated = false;
function applyPublicFeatures(settings) {
    yoloWreckSavingAllowed = reportAdminAuthenticated || !settings || settings.yolo_wrecks !== false;
    document.querySelectorAll('.save-wreck').forEach(btn => {
        btn.hidden = !yoloWreckSavingAllowed;
        btn.disabled = !yoloWreckSavingAllowed;
    });
}
async function loadPublicFeatures() {
    let publicFeatures = {};
    try {
        const resp = await fetch('/api/settings', { cache: 'no-store' });
        const data = await resp.json();
        if (resp.ok) publicFeatures = data.public_features || {};
    } catch (_) {}
    try {
        const resp = await fetch('/api/admin/status', { cache: 'no-store' });
        const data = await resp.json();
        reportAdminAuthenticated = resp.ok && data.authenticated === true;
    } catch (_) {}
    applyPublicFeatures(publicFeatures);
}
async function saveWreck(rank, btn) {
    if (!yoloWreckSavingAllowed) {
        alert(__SAVE_WRECK_DISABLED__);
        return;
    }
    if (btn) {
        btn.disabled = true;
        btn.textContent = __SAVING_WRECK__;
    }
    try {
        const resp = await fetch('/api/wrecks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rank })
        });
        const data = await resp.json();
        if (!resp.ok || data.status !== 'ok') throw new Error(data.error || __SAVE_WRECK_ERROR__);
        if (btn) btn.textContent = data.evidence_created ? __SAVED_WRECK__ : __ALREADY_SAVED_WRECK__;
    } catch (err) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = __SAVE_WRECK__;
        }
        alert(err.message || __SAVE_WRECK_ERROR__);
    }
}
loadPublicFeatures();
</script>"""


def _report_script(lang: str) -> str:
    replacements = {
        "__SAVE_WRECK_DISABLED__": json.dumps(tr(lang, "saveWreckDisabled")),
        "__SAVING_WRECK__": json.dumps(tr(lang, "savingWreck")),
        "__SAVE_WRECK_ERROR__": json.dumps(tr(lang, "saveWreckError")),
        "__SAVED_WRECK__": json.dumps(tr(lang, "savedWreck")),
        "__ALREADY_SAVED_WRECK__": json.dumps(tr(lang, "alreadySavedWreck")),
        "__SAVE_WRECK__": json.dumps(tr(lang, "saveWreck")),
    }
    script = REPORT_SCRIPT_TEMPLATE
    for marker, value in replacements.items():
        script = script.replace(marker, value)
    return script


def _overlay_pin_html(candidate: Candidate, rank: int, img_w: int, img_h: int, lang: str) -> str:
    if img_w <= 0 or img_h <= 0:
        return ""
    pin_x = (candidate.cx / img_w) * 100
    pin_y = (candidate.cy / img_h) * 100
    pin_color = "#10b981" if candidate.score > 0.7 else "#f59e0b" if candidate.score > 0.55 else "#ef4444"
    title = html_lib.escape(tr(lang, "jumpTo", n=rank), quote=True)
    return (
        f'<div class="overlay-pin" id="overlay-pin-{rank}" '
        f'style="left:{pin_x:.3f}%; top:{pin_y:.3f}%; background:{pin_color};" '
        f'onclick="goToCand({rank})" title="{title}">{rank}</div>'
    )


def _observation_status_text(obs: Observation, lang: str) -> str:
    if obs.status == "present":
        status_text = (
            tr(lang, "cell.match", conf=f"{obs.conf:.2f}")
            if obs.conf is not None
            else (obs.reason or tr(lang, "cell.match", conf="?"))
        )
    elif obs.status == "ignored":
        status_text = obs.reason or tr(lang, "cell.skipped")
    else:
        status_text = tr(lang, "cell.missing")
    return html_lib.escape(status_text)


def _crop_cell_html(
    item: ImageItem,
    candidate: Candidate,
    item_idx: int,
    candidate_idx: int,
    asset_version: str,
    lang: str,
) -> str:
    obs = (
        candidate.observations[item_idx]
        if item_idx < len(candidate.observations)
        else Observation(label=item.label, status="missing")
    )
    crop = item.crops[candidate_idx]
    status_text = _observation_status_text(obs, lang)
    label = html_lib.escape(str(item.label))
    if crop and crop.get("file"):
        crop_url = versioned_asset_url(str(crop["file"]), asset_version)
        return (
            f'<div class="crop-cell"><div class="yr">{label}<span>{status_text}</span></div>'
            f'<div class="crop center {obs.status}"><img src="{crop_url}" loading="lazy"></div></div>'
        )
    empty_text = html_lib.escape(tr(lang, "cell.empty"))
    return (
        f'<div class="crop-cell"><div class="yr">{label}<span>{status_text}</span></div>'
        f'<div class="crop empty {obs.status}">{empty_text}</div></div>'
    )


def _verification_links_html(lat: float, lon: float, lang: str) -> str:
    links = external_map_links(lat, lon)
    verify_links = [
        (tr(lang, "link.streetView"), links["street_view"]),
        (tr(lang, "link.gmapsSat"), links["google_maps_satellite"]),
        (tr(lang, "link.appleMaps"), links["apple_maps"]),
        (tr(lang, "link.mapillary"), links["mapillary"]),
        (tr(lang, "link.geoportal"), links["geoportal"]),
    ]
    return " · ".join(
        f'<a href="{html_lib.escape(url, quote=True)}" target="_blank">{html_lib.escape(name)}</a>'
        for name, url in verify_links
    )


def _coords_and_satellite_cell(candidate: Candidate, lang: str) -> tuple[str, str]:
    if candidate.lat is None or candidate.lon is None:
        return "", ""
    lat, lon = candidate.lat, candidate.lon
    coords_html = f'<div class="coords">📍 {lat:.6f}, {lon:.6f} → {_verification_links_html(lat, lon, lang)}</div>'
    sat_url = html_lib.escape(google_maps_embed_url(lat, lon), quote=True)
    satellite_cell = (
        '<div class="crop-cell">'
        f'<div class="yr">{tr(lang, "cell.satellite")}<span>{tr(lang, "cell.googleAge")}</span></div>'
        f'<div class="crop sat"><iframe loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="{sat_url}"></iframe></div>'
        "</div>"
    )
    return coords_html, satellite_cell


def _candidate_grid_html(
    items: list[ImageItem],
    candidate: Candidate,
    candidate_idx: int,
    asset_version: str,
    lang: str,
) -> tuple[str, str]:
    cells = [
        _crop_cell_html(item, candidate, item_idx, candidate_idx, asset_version, lang)
        for item_idx, item in enumerate(items)
    ]
    coords_html, satellite_cell = _coords_and_satellite_cell(candidate, lang)
    if satellite_cell:
        cells.insert(0, satellite_cell)
    return coords_html, "".join(cells)


def _candidate_card_html(
    items: list[ImageItem],
    candidate: Candidate,
    candidate_idx: int,
    asset_version: str,
    lang: str,
) -> str:
    rank = candidate_idx + 1
    coords_html, cells_html = _candidate_grid_html(items, candidate, candidate_idx, asset_version, lang)
    locate_title = html_lib.escape(tr(lang, "showOnMap.title"), quote=True)
    meta = tr(
        lang,
        "candMeta",
        labels=", ".join(candidate.labels_present),
        missing=candidate.clear_missing_count,
        ignored=candidate.ignored_count,
    )
    return f"""
        <div class="cand">
          <div class="cand-head">
            <span class="rank" id="cand-{rank}">#{rank}</span>
            <a class="locate" onclick="showOn({rank}); return false;" href="#overlay-wrap" title="{locate_title}">{tr(lang, "showOnMap")}</a>
            <button type="button" class="save-wreck" onclick="saveWreck({rank}, this)">{tr(lang, "saveWreck")}</button>
            <span class="score" title="{html_lib.escape(tr(lang, "score.tooltip"), quote=True)}">Score <b>{(candidate.score * 100):.0f}%</b></span>
            <span class="badge cov">{tr(lang, "badge.coverage", n=candidate.n_detections, total=candidate.valid_items)}</span>
            <span class="badge col">{tr(lang, "badge.color", pct=f"{candidate.color_consistency * 100:.0f}")}</span>
            <span class="badge cnf">{tr(lang, "badge.yolo", val=f"{candidate.current_conf:.2f}")}</span>
            <span class="badge span">{tr(lang, "badge.span", pct=f"{candidate.span_score * 100:.0f}")}</span>
          </div>
          <div class="cand-meta">{html_lib.escape(meta)}</div>
          {coords_html}
          <div class="grid-wrap">{cells_html}</div>
        </div>
        """


def _legend_html(
    diagnostics_url: str,
    crop_manifest_url: str,
    overlay_url: str,
    overlay_pins_html: str,
    lang: str,
) -> str:
    return f"""<div class="legend">
  <b>{tr(lang, "legend.title")}</b>
  <div style="font-size:11px; color:#94a3b8; margin-top:4px;">{tr(lang, "legend.note")} · <a href="{diagnostics_url}" target="_blank">{tr(lang, "legend.diagnostics")}</a> · <a href="{crop_manifest_url}" target="_blank">{tr(lang, "legend.cropManifest")}</a></div>
  <div class="overlay-wrap" id="overlay-wrap">
    <img src="{overlay_url}" style="width:100%; height:auto; border-radius:10px; margin-top:8px; display:block;">
    {overlay_pins_html}
  </div>
</div>"""


def render_report(
    items: list[ImageItem],
    candidates: list[Candidate],
    output_path: Path,
    asset_version: str,
    img_w: int = 0,
    img_h: int = 0,
    lang: str = "pl",
) -> None:
    diagnostics_url = versioned_asset_url("run_log.json", asset_version)
    crop_manifest_url = versioned_asset_url("crop_manifest.json", asset_version)
    overlay_url = versioned_asset_url("overlays/scored_overlay.jpg", asset_version)
    overlay_pins_html = "".join(
        _overlay_pin_html(candidate, rank, img_w, img_h, lang) for rank, candidate in enumerate(candidates, start=1)
    )
    rows_html = "".join(
        _candidate_card_html(items, candidate, candidate_idx, asset_version, lang)
        for candidate_idx, candidate in enumerate(candidates)
    )
    empty_html = f'<div style="padding:40px;">{html_lib.escape(tr(lang, "noCars"))}</div>'

    html = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<title>{tr(lang, "title")}</title>
<base href="./">
{REPORT_CSS}</head><body>
{_legend_html(diagnostics_url, crop_manifest_url, overlay_url, overlay_pins_html, lang)}
{rows_html or empty_html}
{_report_script(lang)}
</body></html>"""
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
    with output_path.open("w", encoding="utf-8") as f:
        f.write(html)
