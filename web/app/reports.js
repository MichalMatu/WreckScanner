function localDatetimeValue(date = new Date()) {
    const pad = n => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

let reportPdfDownloadUrls = [];
let reportPdfTarget = null;

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
    form?.reset();
    revokeReportPdfDownloadUrls();
    reportPdfTarget = target;
    updatePublicFeatureAccess();
    const observedAt = form?.querySelector('[name="observed_at"]');
    if (observedAt) observedAt.value = localDatetimeValue();
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
}

async function submitReportPdf(event) {
    event.preventDefault();
    const form = document.getElementById('report-pdf-form');
    const status = document.getElementById('report-pdf-status');
    const submit = document.getElementById('report-pdf-submit');
    const result = document.getElementById('report-pdf-result');
    const target = reportPdfTarget;
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
        const data = await apiJson(reportUrl, {
            method: 'POST',
            body: formData,
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
        if (result) result.hidden = true;
        if (submit) submit.hidden = false;
        if (status) status.textContent = apiErrorMessage(err, t('modal.report.generateError'));
    } finally {
        if (submit) {
            submit.disabled = false;
            submit.querySelector('span').textContent = t('modal.report.submit');
        }
    }
}
