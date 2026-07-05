function openWelcomeModalIfNeeded() {
    try {
        if (localStorage.getItem(WELCOME_MODAL_SEEN_STORAGE_KEY) === '1') return;
        localStorage.setItem(WELCOME_MODAL_SEEN_STORAGE_KEY, '1');
    } catch (_) {}

    window.setTimeout(() => {
        if (document.querySelector('.modal-backdrop:not([hidden])')) return;
        openModal('modal-help');
    }, 350);
}

function openWelcomeModalFromAdminPanel() {
    try {
        localStorage.removeItem(WELCOME_MODAL_SEEN_STORAGE_KEY);
    } catch (_) {}
    openAdminChildModal('modal-help');
}

openWelcomeModalIfNeeded();
