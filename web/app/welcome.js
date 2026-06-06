function openWelcomeModalIfNeeded() {
    try {
        if (localStorage.getItem(WELCOME_MODAL_SEEN_STORAGE_KEY) === '1') return;
        localStorage.setItem(WELCOME_MODAL_SEEN_STORAGE_KEY, '1');
        localStorage.removeItem(`${MODAL_POSITION_STORAGE_PREFIX}modal-help`);
    } catch (_) {}

    window.setTimeout(() => {
        if (document.querySelector('.modal-backdrop:not([hidden])')) return;
        openModal('modal-help');
    }, 350);
}

function openWelcomeModalFromAdminPanel() {
    try {
        localStorage.removeItem(WELCOME_MODAL_SEEN_STORAGE_KEY);
        localStorage.removeItem(`${MODAL_POSITION_STORAGE_PREFIX}modal-help`);
    } catch (_) {}
    closeModal(document.getElementById('modal-admin-panel'));
    openModal('modal-help');
}

openWelcomeModalIfNeeded();
