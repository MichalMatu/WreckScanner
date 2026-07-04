function openProblemReportModal() {
    const status = document.getElementById('privacy-request-submit-status');
    if (status) status.textContent = '';
    openModal('modal-problem-report');
    requestAnimationFrame(() => {
        document.querySelector('#privacy-request-form input[name="email"]')?.focus();
    });
}

function openPrivacyInfoModal() {
    openModal('modal-privacy-info');
}

async function submitPrivacyRequest(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const submit = document.getElementById('privacy-request-submit');
    const status = document.getElementById('privacy-request-submit-status');
    const data = Object.fromEntries(new FormData(form).entries());

    if (status) status.textContent = t('page.report.sending');
    if (submit) submit.disabled = true;
    try {
        const payload = await apiPostJson('/api/privacy-requests', data);
        if (payload.status !== 'ok') {
            throw new ApiError(payload.error || t('page.report.saveError'), { payload });
        }
        form.reset();
        if (status) status.textContent = t('page.report.saved', { id: payload.request_id });
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('page.report.saveError'));
    } finally {
        if (submit) submit.disabled = false;
    }
}

document.addEventListener('click', event => {
    const link = event.target.closest('a[href="/report"], a[href="/privacy"]');
    if (!link) return;
    event.preventDefault();
    if (link.getAttribute('href') === '/report') {
        openProblemReportModal();
        return;
    }
    openPrivacyInfoModal();
});

requestAnimationFrame(() => {
    if (window.location.pathname === '/report') {
        openProblemReportModal();
    } else if (window.location.pathname === '/privacy') {
        openPrivacyInfoModal();
    }
});
