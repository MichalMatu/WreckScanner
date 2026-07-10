function localDatetimeValue(date = new Date()) {
    const pad = n => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

let reportPdfDownloadUrls = [];
let reportPdfTarget = null;
let reportPdfDefaultLocationDescription = '';
let reportPdfAbortController = null;

function reportFormField(form, name) {
    return form?.querySelector(`[name="${name}"]`) || null;
}

function setReportFormValue(form, name, value) {
    const field = reportFormField(form, name);
    if (!field || field.value) return;
    field.value = value;
}

try { localStorage.removeItem('wreckscanner.reportReporter.v1'); } catch (_) {}

function applyReportDescriptionDefaults(form, target) {
    const lat = Number(target?.lat);
    const lon = Number(target?.lon);
    const coords = {
        lat: Number.isFinite(lat) ? lat.toFixed(6) : '',
        lon: Number.isFinite(lon) ? lon.toFixed(6) : '',
    };
    reportPdfDefaultLocationDescription = t('modal.report.defaultLocation', coords);
    setReportFormValue(form, 'location_description', reportPdfDefaultLocationDescription);
    setReportFormValue(form, 'vehicle_description', t('modal.report.defaultVehicleDescription'));
}

async function applyReportAddressDefault(form, target) {
    const lat = Number(target?.lat);
    const lon = Number(target?.lon);
    const locationField = reportFormField(form, 'location_description');
    if (!locationField || !Number.isFinite(lat) || !Number.isFinite(lon)) return;
    const expectedDefault = reportPdfDefaultLocationDescription;
    try {
        const params = new URLSearchParams({ lat: String(lat), lon: String(lon) });
        const data = await apiJson(`${ADDRESS_REVERSE_URL}?${params}`);
        const address = String(data?.address?.formatted || '').trim();
        if (!address || target !== reportPdfTarget) return;
        const current = String(locationField.value || '');
        if (current && current !== expectedDefault) return;
        reportPdfDefaultLocationDescription = t('modal.report.defaultLocationWithAddress', { address });
        locationField.value = reportPdfDefaultLocationDescription;
    } catch (_) {}
}

function revokeReportPdfDownloadUrls() {
    for (const url of reportPdfDownloadUrls) {
        URL.revokeObjectURL(url);
    }
    reportPdfDownloadUrls = [];
}

function reportPdfBlobUrl(base64, contentType) {
    const binary = atob(base64 || '');
    const chunks = [];
    for (let offset = 0; offset < binary.length; offset += 8192) {
        const slice = binary.slice(offset, offset + 8192);
        const bytes = new Uint8Array(slice.length);
        for (let index = 0; index < slice.length; index += 1) {
            bytes[index] = slice.charCodeAt(index);
        }
        chunks.push(bytes);
    }
    const url = URL.createObjectURL(new Blob(chunks, { type: contentType }));
    reportPdfDownloadUrls.push(url);
    return url;
}

function resetReportPdfModal(target) {
    const form = document.getElementById('report-pdf-form');
    const result = document.getElementById('report-pdf-result');
    const status = document.getElementById('report-pdf-status');
    const submit = document.getElementById('report-pdf-submit');
    reportPdfAbortController?.abort();
    reportPdfAbortController = null;
    form?.reset();
    revokeReportPdfDownloadUrls();
    reportPdfTarget = target;
    updatePublicFeatureAccess();
    const observedAt = form?.querySelector('[name="observed_at"]');
    if (observedAt) observedAt.value = localDatetimeValue();
    applyReportDescriptionDefaults(form, target);
    if (result) result.hidden = true;
    if (status) status.textContent = '';
    if (submit) {
        submit.hidden = false;
        submit.disabled = false;
        submit.querySelector('span').textContent = t('modal.report.submit');
    }
}

async function openFieldPhotoReportPdfModal(lat, lon, photoIds) {
    const latNumber = Number(lat);
    const lonNumber = Number(lon);
    const safePhotoIds = (photoIds || []).map(safeFieldPhotoId).filter(Boolean);
    if (!Number.isFinite(latNumber) || !Number.isFinite(lonNumber) || !safePhotoIds.length) return;
    resetReportPdfModal({
        type: 'field-photos',
        lat: latNumber,
        lon: lonNumber,
        photoIds: safePhotoIds,
    });
    openModal('modal-report-pdf');
    applyReportAddressDefault(document.getElementById('report-pdf-form'), reportPdfTarget);
}

async function submitReportPdf(event) {
    event.preventDefault();
    const form = document.getElementById('report-pdf-form');
    const status = document.getElementById('report-pdf-status');
    const submit = document.getElementById('report-pdf-submit');
    const result = document.getElementById('report-pdf-result');
    const target = reportPdfTarget;
    let requestController = null;
    if (!form || !target) return;
    if (!form.reportValidity()) return;

    if (submit) {
        submit.hidden = false;
        submit.disabled = true;
        submit.querySelector('span').textContent = t('modal.report.generating');
    }
    if (status) status.textContent = t('modal.report.generating');
    if (result) result.hidden = true;

    try {
        const formData = new FormData(form);
        if (target.type !== 'field-photos') throw new Error(t('modal.report.generateError'));
        formData.set('photo_ids', JSON.stringify(target.photoIds || []));
        formData.set('lat', String(target.lat));
        formData.set('lon', String(target.lon));
        const reportUrl = '/api/field-photo-reports/report-pdf';
        requestController = new AbortController();
        reportPdfAbortController = requestController;
        const data = await apiJson(reportUrl, {
            method: 'POST',
            body: formData,
            signal: requestController.signal,
            timeoutMs: API_REPORT_TIMEOUT_MS,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.report.generateError'));
        }
        if (!data.pdf_filename || !data.pdf_base64) {
            throw new Error(t('modal.report.generateError'));
        }
        revokeReportPdfDownloadUrls();
        const pdfLink = document.getElementById('report-pdf-download');
        if (pdfLink) {
            pdfLink.href = reportPdfBlobUrl(data.pdf_base64, 'application/pdf');
            pdfLink.download = data.pdf_filename;
        }
        if (submit) submit.hidden = true;
        if (result) result.hidden = false;
        if (status) status.textContent = '';
    } catch (err) {
        if (err?.payload?.code === 'cancelled' && reportPdfTarget !== target) return;
        if (result) result.hidden = true;
        if (submit) submit.hidden = false;
        if (status) status.textContent = apiErrorMessage(err, t('modal.report.generateError'));
    } finally {
        if (reportPdfAbortController === requestController) reportPdfAbortController = null;
        if (submit && reportPdfTarget === target) {
            submit.disabled = false;
            submit.querySelector('span').textContent = t('modal.report.submit');
        }
    }
}

document.getElementById('modal-report-pdf')?.addEventListener('modalclose', () => {
    reportPdfTarget = null;
    reportPdfAbortController?.abort();
    reportPdfAbortController = null;
    revokeReportPdfDownloadUrls();
});
