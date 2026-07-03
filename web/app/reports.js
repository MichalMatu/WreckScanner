function resetWreckPhotoModal(wreckId) {
    const form = document.getElementById('wreck-photo-form');
    const status = document.getElementById('wreck-photo-status');
    const submit = document.getElementById('wreck-photo-submit');
    const filesInput = document.getElementById('wreck-photo-files');
    form?.reset();
    updateFilePickerSummary(filesInput);
    document.getElementById('wreck-photo-wreck-id').value = wreckId;
    if (status) status.textContent = '';
    if (submit) {
        submit.disabled = false;
        submit.querySelector('span').textContent = t('modal.wreckPhoto.submit');
    }
}

async function openWreckPhotoModal(wreckId) {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)) return;
    const id = safeWreckId(wreckId);
    if (!id) return;
    resetWreckPhotoModal(id);
    openModal('modal-wreck-photo-upload');
}

function validateWreckPhotoFiles(files) {
    const photoFiles = Array.from(files || []);
    if (!photoFiles.length) {
        throw new Error(t('modal.wreckPhoto.noFiles'));
    }
    if (photoFiles.length > WRECK_PHOTO_MAX_COUNT) {
        throw new Error(t('modal.wreckPhoto.fileCountError', { n: WRECK_PHOTO_MAX_COUNT }));
    }
    for (const file of photoFiles) {
        if (file.size > WRECK_PHOTO_MAX_BYTES) {
            throw new Error(t('modal.wreckPhoto.fileLimitError'));
        }
        if (file.type && !FIELD_PHOTO_ALLOWED_TYPES.has(file.type)) {
            throw new Error(t('modal.wreckPhoto.fileTypeError'));
        }
    }
}

async function submitWreckPhotoUpload(event) {
    event.preventDefault();
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)) return;
    const form = document.getElementById('wreck-photo-form');
    const wreckId = safeWreckId(document.getElementById('wreck-photo-wreck-id')?.value);
    const status = document.getElementById('wreck-photo-status');
    const submit = document.getElementById('wreck-photo-submit');
    if (!form || !wreckId) return;

    try {
        validateWreckPhotoFiles(document.getElementById('wreck-photo-files')?.files);
    } catch (err) {
        if (status) status.textContent = err.message;
        return;
    }

    if (submit) {
        submit.disabled = true;
        submit.querySelector('span').textContent = t('modal.wreckPhoto.uploading');
    }
    if (status) status.textContent = t('modal.wreckPhoto.uploading');

    try {
        const data = await apiJson(`${WRECKS_URL}/${encodeURIComponent(wreckId)}/photos`, {
            method: 'POST',
            body: new FormData(form),
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.wreckPhoto.saveError'));
        }
        await loadSavedWrecks();
        closeModal();
        statusEl.textContent = t('modal.wreckPhoto.saved', { n: data.photo_count || 0 });
        statusEl.className = 'ok';
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.wreckPhoto.saveError'));
    } finally {
        if (submit) {
            submit.disabled = false;
            submit.querySelector('span').textContent = t('modal.wreckPhoto.submit');
        }
    }
}

function localDatetimeValue(date = new Date()) {
    const pad = n => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

let reportPackageDownloadUrls = [];

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

function resetReportPackageModal(wreckId) {
    const form = document.getElementById('report-package-form');
    const result = document.getElementById('report-package-result');
    const status = document.getElementById('report-package-status');
    const submit = document.getElementById('report-package-submit');
    form?.reset();
    revokeReportPackageDownloadUrls();
    updatePublicFeatureAccess();
    document.getElementById('report-wreck-id').value = wreckId;
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

async function openReportPackageModal(wreckId) {
    const id = safeWreckId(wreckId);
    if (!id) return;
    resetReportPackageModal(id);
    openModal('modal-report-package');
}

async function submitReportPackage(event) {
    event.preventDefault();
    const form = document.getElementById('report-package-form');
    const wreckId = safeWreckId(document.getElementById('report-wreck-id')?.value);
    const status = document.getElementById('report-package-status');
    const submit = document.getElementById('report-package-submit');
    const result = document.getElementById('report-package-result');
    if (!form || !wreckId) return;
    if (!form.reportValidity()) return;

    if (submit) {
        submit.hidden = false;
        submit.disabled = true;
        submit.querySelector('span').textContent = t('modal.report.generating');
    }
    if (status) status.textContent = t('modal.report.generating');
    if (result) result.hidden = true;

    try {
        const reportPath = adminAuthenticated ? 'report-package' : 'public-report-package';
        const formData = new FormData(form);
        const data = await apiJson(`${WRECKS_URL}/${encodeURIComponent(wreckId)}/${reportPath}`, {
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
