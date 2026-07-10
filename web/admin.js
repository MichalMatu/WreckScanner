let adminAuthenticated = false;
let pendingAdminLoginResolve = null;

function setAdminAuthenticated(value) {
    const previous = adminAuthenticated;
    adminAuthenticated = Boolean(value);
    document.querySelectorAll('.admin-only').forEach(el => { el.hidden = !adminAuthenticated; });
    if (typeof updateSettingsAccess === 'function') updateSettingsAccess();
    if (typeof updatePublicLayerAccess === 'function') updatePublicLayerAccess();
    const btn = document.getElementById('admin-login');
    if (btn) {
        btn.classList.toggle('is-admin', adminAuthenticated);
        btn.title = adminAuthenticated ? t('icon.adminLogout') : t('icon.adminLogin');
    }
    const panelBtn = document.getElementById('open-admin-panel');
    if (panelBtn) {
        panelBtn.classList.toggle('is-admin', adminAuthenticated);
    }
    if (previous !== adminAuthenticated) {
        if (typeof loadFieldPhotos === 'function') {
            loadFieldPhotos();
        }
    }
}

async function refreshAdminStatus() {
    try {
        const data = await apiJson(ADMIN_STATUS_URL, { cache: 'no-store', handleAdminSession: false });
        setAdminAuthenticated(data.authenticated === true);
    } catch (_) {
        setAdminAuthenticated(false);
    }
}

async function adminLogin() {
    if (adminAuthenticated) return true;
    return new Promise(resolve => {
        pendingAdminLoginResolve = resolve;
        const form = document.getElementById('admin-login-form');
        const status = document.getElementById('admin-login-status');
        const submit = document.getElementById('admin-login-submit');
        form?.reset();
        if (status) status.textContent = '';
        if (submit) {
            submit.disabled = false;
            submit.querySelector('span').textContent = t('modal.admin.submit');
        }
        openModal('modal-admin-login');
        requestAnimationFrame(() => document.getElementById('admin-password-input')?.focus());
    });
}

function closeAdminLoginModal(success = false, target = null) {
    if (target instanceof Element && !target.classList.contains('modal-backdrop')) return;
    const modal = document.getElementById('modal-admin-login');
    if (modal) hideModalBackdrop(modal);
    if (!success && pendingAdminLoginResolve) {
        pendingAdminLoginResolve(false);
        pendingAdminLoginResolve = null;
    }
}

async function submitAdminLogin(event) {
    event.preventDefault();
    const passwordInput = document.getElementById('admin-password-input');
    const status = document.getElementById('admin-login-status');
    const submit = document.getElementById('admin-login-submit');
    const password = passwordInput?.value || '';
    if (!password) return;
    if (submit) {
        submit.disabled = true;
        submit.querySelector('span').textContent = t('modal.admin.loggingIn');
    }
    if (status) status.textContent = '';
    try {
        const data = await apiPostJson(ADMIN_LOGIN_URL, { password }, { handleAdminSession: false });
        if (data.authenticated !== true) throw new Error(data.error || t('admin.loginError'));
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('admin.loginError'));
        setAdminAuthenticated(false);
        if (submit) {
            submit.disabled = false;
            submit.querySelector('span').textContent = t('modal.admin.submit');
        }
        passwordInput?.focus();
        return;
    }
    setAdminAuthenticated(true);
    if (pendingAdminLoginResolve) {
        pendingAdminLoginResolve(true);
        pendingAdminLoginResolve = null;
    }
    closeAdminLoginModal(true);
}

async function toggleAdminLogin() {
    if (adminAuthenticated) {
        await apiJson(ADMIN_LOGOUT_URL, { method: 'POST', handleAdminSession: false }).catch(() => {});
        setAdminAuthenticated(false);
        closeModal();
        return;
    }
    await adminLogin();
}

document.addEventListener('adminsessionexpired', () => {
    setAdminAuthenticated(false);
    const status = document.getElementById('status');
    if (status) {
        status.classList.add('is-error');
        status.textContent = apiLocalizedText(
            'admin.sessionExpired',
            'Sesja administratora wygasła. Zaloguj się ponownie przed ponowieniem operacji.',
        );
    }
});

async function ensureAdmin() {
    if (adminAuthenticated) return true;
    await refreshAdminStatus();
    if (adminAuthenticated) return true;
    return adminLogin();
}

async function openSettingsModal() {
    await refreshAdminStatus();
    if (typeof updateSettingsAccess === 'function') updateSettingsAccess();
    openModal('modal-settings');
}

function isAdminPanelOpen() {
    const modal = document.getElementById('modal-admin-panel');
    return Boolean(modal && !modal.hidden);
}

function openAdminChildModal(id) {
    openModal(id, { preserveOpen: isAdminPanelOpen() });
}

async function openAdminPanel() {
    if (!(await ensureAdmin())) return;
    if (typeof updatePublicLayerAccess === 'function') updatePublicLayerAccess();
    openModal('modal-admin-panel');
}

async function openPhotoRetentionModal() {
    if (!(await ensureAdmin())) return;
    openAdminChildModal('modal-photo-retention');
    if (typeof loadPhotoRetentionStatus === 'function') loadPhotoRetentionStatus();
}
