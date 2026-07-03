function localDatetimeValue(date = new Date()) {
    const pad = n => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

let reportPackageDownloadUrls = [];
let reportPackageTarget = null;

function revokeReportPackageDownloadUrls() {
    for (const url of reportPackageDownloadUrls) {
        URL.revokeObjectURL(url);
    }
    reportPackageDownloadUrls = [];
}

function reportPackageBlobUrl(base64, contentType) {
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
    reportPackageDownloadUrls.push(url);
    return url;
}

function resetReportPackageModal(target) {
    const form = document.getElementById('report-package-form');
    const result = document.getElementById('report-package-result');
    const status = document.getElementById('report-package-status');
    const submit = document.getElementById('report-package-submit');
    form?.reset();
    revokeReportPackageDownloadUrls();
    reportPackageTarget = target;
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

async function openFieldPhotoReportPackageModal(lat, lon, photoIds) {
    const latNumber = Number(lat);
    const lonNumber = Number(lon);
    const safePhotoIds = (photoIds || []).map(safeFieldPhotoId).filter(Boolean);
    if (!Number.isFinite(latNumber) || !Number.isFinite(lonNumber) || !safePhotoIds.length) return;
    resetReportPackageModal({
        type: 'field-photos',
        lat: latNumber,
        lon: lonNumber,
        photoIds: safePhotoIds,
    });
    openModal('modal-report-package');
}

async function submitReportPackage(event) {
    event.preventDefault();
    const form = document.getElementById('report-package-form');
    const status = document.getElementById('report-package-status');
    const submit = document.getElementById('report-package-submit');
    const result = document.getElementById('report-package-result');
    const target = reportPackageTarget;
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
        if (target.type !== 'field-photos') throw new Error(t('wreck.reportPackageError'));
        formData.set('photo_ids', JSON.stringify(target.photoIds || []));
        formData.set('lat', String(target.lat));
        formData.set('lon', String(target.lon));
        const reportUrl = '/api/field-photo-reports/report-package';
        const data = await apiJson(reportUrl, {
            method: 'POST',
            body: formData,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('wreck.reportPackageError'));
        }
        if (!data.zip_filename || !data.pdf_filename || !data.zip_base64 || !data.pdf_base64) {
            throw new Error(t('wreck.reportPackageError'));
        }
        revokeReportPackageDownloadUrls();
        const zipLink = document.getElementById('report-package-download');
        const pdfLink = document.getElementById('report-package-pdf');
        if (zipLink) {
            zipLink.href = reportPackageBlobUrl(data.zip_base64, 'application/zip');
            zipLink.download = data.zip_filename;
        }
        if (pdfLink) {
            pdfLink.href = reportPackageBlobUrl(data.pdf_base64, 'application/pdf');
            pdfLink.download = data.pdf_filename;
        }
        if (submit) submit.hidden = true;
        if (result) result.hidden = false;
        if (status) status.textContent = '';
    } catch (err) {
        if (result) result.hidden = true;
        if (submit) submit.hidden = false;
        if (status) status.textContent = apiErrorMessage(err, t('wreck.reportPackageError'));
    } finally {
        if (submit) {
            submit.disabled = false;
            submit.querySelector('span').textContent = t('modal.report.submit');
        }
    }
}
