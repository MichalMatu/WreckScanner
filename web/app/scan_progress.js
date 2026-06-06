let downloadProgressTimer = null;
const stepTimers = {};

function setStep(id, state, label = null, meta = null) {
    const el = document.getElementById('step-' + id);
    if (!el) return;
    el.classList.remove('active', 'done', 'error');
    if (state !== 'pending') el.classList.add(state);

    if (label) el.querySelector('.step-label').textContent = label;

    const metaEl = el.querySelector('.step-meta');
    if (meta) {
        metaEl.textContent = meta;
        metaEl.classList.add('show');
    } else {
        metaEl.textContent = '';
        metaEl.classList.remove('show');
    }

    if (stepTimers[id]) {
        clearInterval(stepTimers[id].interval);
        delete stepTimers[id];
    }
    if (state === 'active') {
        const timeEl = el.querySelector('.step-time');
        const start = Date.now();
        timeEl.textContent = '0:00';
        stepTimers[id] = {
            interval: setInterval(() => {
                const s = Math.floor((Date.now() - start) / 1000);
                timeEl.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
            }, STEP_TIMER_INTERVAL_MS),
        };
    }
}

function setStepMeta(id, meta) {
    const el = document.getElementById('step-' + id);
    const metaEl = el?.querySelector('.step-meta');
    if (!metaEl) return;
    if (meta) {
        metaEl.textContent = meta;
        metaEl.classList.add('show');
    } else {
        metaEl.textContent = '';
        metaEl.classList.remove('show');
    }
}

function setStepProgress(id, percent = null, indeterminate = false) {
    const el = document.getElementById('step-' + id);
    const bar = el?.querySelector('.step-progress');
    const fill = bar?.querySelector('div');
    if (!bar || !fill) return;
    const show = indeterminate || Number.isFinite(percent);
    bar.classList.toggle('show', show);
    bar.classList.toggle('indeterminate', Boolean(indeterminate));
    if (Number.isFinite(percent)) {
        fill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    } else if (!indeterminate) {
        fill.style.width = '0%';
    }
}

function formatBytes(bytes) {
    const n = Number(bytes);
    if (!Number.isFinite(n) || n <= 0) return '';
    if (n >= 1024 * 1024 * 1024) return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(0)} MB`;
    return `${(n / 1024).toFixed(0)} KB`;
}

function downloadProgressMeta(data) {
    if (!data || data.status !== 'active') return null;
    if (data.stage === 'wfs_download') {
        const done = formatBytes(data.bytes_done);
        const total = formatBytes(data.bytes_total);
        if (done && total) return `${data.message} · ${done}/${total}`;
        return data.message || t('step.download.wfsDownloading');
    }
    if (data.stage === 'wfs_cache') return data.message || t('step.download.wfsCache');
    return data.message || null;
}

function startDownloadProgressPolling() {
    stopDownloadProgressPolling();
    const poll = async () => {
        try {
            const data = await apiJson(`${DOWNLOAD_PROGRESS_URL}?ts=${Date.now()}`, { cache: 'no-store' });
            if (data.status === 'active') {
                const percent = Number.isFinite(Number(data.percent)) ? Number(data.percent) : null;
                const indeterminate = percent === null;
                const meta = downloadProgressMeta(data);
                if (meta) setStepMeta('download', meta);
                setStepProgress('download', percent, indeterminate);
            }
        } catch (_) {
            setStepProgress('download', null, true);
        }
    };
    poll();
    downloadProgressTimer = setInterval(poll, DOWNLOAD_PROGRESS_POLL_MS);
}

function stopDownloadProgressPolling() {
    if (downloadProgressTimer) {
        clearInterval(downloadProgressTimer);
        downloadProgressTimer = null;
    }
}

function resetProgress() {
    ['download', 'detect'].forEach(id => {
        const el = document.getElementById('step-' + id);
        el.classList.remove('active', 'done', 'error');
        el.querySelector('.step-time').textContent = '';
        const metaEl = el.querySelector('.step-meta');
        metaEl.textContent = '';
        metaEl.classList.remove('show');
        setStepProgress(id, null, false);
        if (stepTimers[id]) { clearInterval(stepTimers[id].interval); delete stepTimers[id]; }
    });
    document.querySelector('#step-download .step-label').textContent = t('step.download.label');
    document.querySelector('#step-detect .step-label').textContent = t('step.detect.label');
    progressEl.hidden = true;
    resultActions.hidden = true;
}
