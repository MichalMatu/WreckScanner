function selectedReviewCropM() {
    const cropM = parseFloat(document.getElementById('crop-select')?.value);
    return Number.isFinite(cropM) ? cropM : 7.5;
}

async function runAll() {
    if (btnRun.disabled || !publicFeatureAllowed(PUBLIC_FEATURE_KEYS.scanAnalysis)) return;
    const center = map.getCenter();
    const lat = center.lat;
    const lon = center.lng;
    const width = currentWidth;
    const height = currentHeight;
    const model = document.getElementById('model-select').value;
    const modelName = model.includes('m-obb') ? 'Medium' : 'Small';
    const conf = parseFloat(document.getElementById('conf-select').value);
    const cropM = selectedReviewCropM();

    let dlData = null;

    clearResults();
    progressEl.hidden = false;
    setStep('download', 'active', t('step.download.label'), t('step.download.area', { w: width, h: height }));
    setStep('detect', 'pending');

    btnRun.disabled = true;
    spinner.style.display = 'block';
    runIcon.style.display = 'none';

    startDownloadProgressPolling();
    try {
        dlData = await apiPostJson(API_URL, { lat, lon, width, height });
        if (dlData.status !== 'completed') {
            currentJobToken = null;
            setStep('download', 'error', t('step.download.error'), dlData.error || t('step.download.unknownError'));
            setStepProgress('download', null, false);
            return;
        }
        const okCount = dlData.saved || 0;
        const missingCount = dlData.missing || 0;
        const totalCount = dlData.total || 0;
        const wfsReplaced = dlData.wfs_replaced || 0;
        const wfsCacheHits = dlData.wfs_cache_hits || 0;
        const wfsDownloaded = dlData.wfs_downloaded || 0;
        currentJobToken = dlData.job_token || null;
        lastDownload = { lat, lon, width, height };

        let metaParts = [];
        if (missingCount > 0) metaParts.push(t('step.download.missing', { n: missingCount }));
        if (wfsReplaced > 0) metaParts.push(t('step.download.wfs', { n: wfsReplaced, cached: wfsCacheHits, downloaded: wfsDownloaded }));
        const meta = metaParts.length ? metaParts.join(' · ') : null;

        setStep('download', 'done', t('step.download.done', { ok: okCount, total: totalCount }), meta);
        setStepProgress('download', 100, false);
    } catch (err) {
        currentJobToken = null;
        setStep('download', 'error', t('step.network.error'), err.message);
        setStepProgress('download', null, false);
        return;
    } finally {
        stopDownloadProgressPolling();
    }

    setStep('detect', 'active', t('step.detect.label'), t('step.detect.model', { name: modelName }));
    try {
        const anData = await apiPostJson(ANALYZE_URL, {
            model,
            lang: CURRENT_LANG,
            conf,
            cropM,
            job_token: currentJobToken,
        });
        if (anData.status === 'ok') {
            const reportLink = anData.report_url;
            const candidates = anData.candidates || [];
            const n = candidates.length;
            setStep('detect', 'done', n > 0 ? t(`step.detect.${carsForm(n)}`, { n }) : t('step.detect.none'));

            if (dlData.bbox) {
                const bboxParts = dlData.bbox.split(',');
                const bounds = [[parseFloat(bboxParts[0]), parseFloat(bboxParts[1])], [parseFloat(bboxParts[2]), parseFloat(bboxParts[3])]];
                const overlayUrl = `/analiza/overlays/scored_overlay.jpg?ts=${Date.now()}`;
                imageOverlay = L.imageOverlay(overlayUrl, bounds, { opacity: 1.0, zIndex: 400 }).addTo(map);
                scanArea = L.rectangle(bounds, { color: '#fbbf24', weight: 2, fillOpacity: 0, dashArray: '6,4', interactive: false }).addTo(map);
            }

            placeMarkers(candidates, reportLink);

            btnReport.href = reportLink;
            reportLabelEl.textContent = t('result.reportShort');
            resultActions.hidden = false;
        } else {
            const errTxt = (anData.stderr || anData.error || '').split('\n').slice(-2).join(' ');
            setStep('detect', 'error', t('step.detect.error'), errTxt);
        }
    } catch (err) {
        setStep('detect', 'error', t('step.detect.networkError'), err.message);
    } finally {
        currentJobToken = null;
        btnRun.disabled = false;
        spinner.style.display = 'none';
        runIcon.style.display = 'block';
    }
}

function placeMarkers(candidates, reportLink) {
    const withCoords = candidates.filter(c => c.lat && c.lon);
    if (!withCoords.length) return;
    const yoloWrecksAllowed = publicFeatureAllowed(PUBLIC_FEATURE_KEYS.yoloWrecks);
    withCoords.forEach(c => {
        const sv = `https://www.google.com/maps/@${c.lat},${c.lon},3a,75y,90h,75t/data=!3m6!1e1`;
        const gmap = `https://www.google.com/maps/@${c.lat},${c.lon},80m/data=!3m1!1e3`;
        const amap = `https://maps.apple.com/?ll=${c.lat},${c.lon}&z=20&t=k`;
        const mapil = `https://www.mapillary.com/app/?lat=${c.lat}&lng=${c.lon}&z=19`;
        const geop = `https://mapy.geoportal.gov.pl/imap/Imgp_2.html?gpmap=gp0&lat=${c.lat}&lon=${c.lon}`;
        const saveButton = yoloWrecksAllowed
            ? `<button type="button" class="map-popup-text-action" data-yolo-wreck-save onclick="saveWreck(${c.rank}, this)">${t('wreck.save')}</button>`
            : '';
        const candidateLinks = [
            popupCompactLink(sv, t('popup.streetView'), t('popup.streetView')),
            popupCompactLink(gmap, t('popup.gmapsSat'), t('popup.gmapsSat')),
            popupCompactLink(amap, t('popup.appleMaps'), t('popup.appleMaps')),
            popupCompactLink(mapil, t('popup.mapillary'), t('popup.mapillary')),
            popupCompactLink(geop, t('popup.geoportal'), t('popup.geoportal')),
            popupCompactLink(reportLink, t('popup.report'), t('popup.report')),
        ];
        const popupHtml = `
            <div class="map-popup map-popup--candidate">
                ${popupHeader(t('popup.candidateTitle', { rank: c.rank }), `${(c.score * 100).toFixed(0)}%`)}
                ${popupMeta([
                    t('popup.metrics', { cov: (c.coverage * 100).toFixed(0), col: (c.color_consistency * 100).toFixed(0) }),
                    t('popup.present', { labels: c.labels_present.join(', ') }),
                    `${c.lat.toFixed(6)}, ${c.lon.toFixed(6)}`,
                ])}
                ${popupLinks(candidateLinks)}
                ${popupActions([saveButton])}
            </div>`;
        const marker = L.marker([c.lat, c.lon], { icon: pinIcon(c.rank, c.score) })
            .addTo(map)
            .bindPopup(popupHtml);
        candidateMarkers.push(marker);
    });
    if (candidateMarkers.length > 0) {
        const group = L.featureGroup(candidateMarkers);
        map.fitBounds(group.getBounds().pad(0.15));
    }
}

map.on('click', async (e) => {
    if (e.originalEvent.shiftKey) return;
    if (isFieldPhotoLocationPickActive()) return;
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.manualWrecks)) return;
    if (!lastDownload) return;
    const inspectLat = Number(e.latlng.lat);
    const inspectLon = Number(e.latlng.lng);
    if (!Number.isFinite(inspectLat) || !Number.isFinite(inspectLon)) return;

    const lat_m = METERS_PER_DEGREE_LAT;
    const lon_m = METERS_PER_DEGREE_LAT * Math.cos(lastDownload.lat * Math.PI / 180);
    const dLatM = Math.abs(inspectLat - lastDownload.lat) * lat_m;
    const dLonM = Math.abs(inspectLon - lastDownload.lon) * lon_m;
    if (dLatM > lastDownload.height / 2 || dLonM > lastDownload.width / 2) return;

    const popup = L.popup({ maxWidth: 300 })
        .setLatLng([inspectLat, inspectLon])
        .setContent(`<div style="text-align:center; padding:10px;">${t('inspect.loading')}</div>`)
        .openOn(map);

    try {
        const data = await apiPostJson('/api/inspect', {
            lat: inspectLat,
            lon: inspectLon,
            cropM: selectedReviewCropM(),
        });
        if (data.status !== 'ok' || !Array.isArray(data.crops) || data.crops.length === 0) {
            map.closePopup(popup);
            return;
        }

        const cropPreviews = data.crops.map(c => ({
            source: 'inspect',
            label: c.year,
            public_image: c.url,
            public_thumb: c.url,
        }));

        const content = `
            <div class="map-popup map-popup--manual-inspect">
                ${popupHeader(t('inspect.title'))}
                ${popupMeta([t('inspect.coords', { lat: inspectLat.toFixed(6), lon: inspectLon.toFixed(6) })])}
                ${popupPhotoSection(t('wreck.popup.evidencePreviews'), cropPreviews)}
                ${popupActions([`<button type="button" class="map-popup-text-action" onclick="saveManualWreck(${inspectLat.toFixed(8)}, ${inspectLon.toFixed(8)}, this)">${t('inspect.saveWreck')}</button>`])}
            </div>
        `;
        popup.setContent(content);
    } catch (err) {
        map.closePopup(popup);
    }
});
