// ─── APP MENU ───────────────────────────────────
// Główne menu aplikacji łączy nawigację, akcje mapy i filtry warstw.
function isAppMenuOpen() {
    return Boolean(document.body?.classList.contains('app-menu-open'));
}

function updateAppMenuState() {
    const isOpen = isAppMenuOpen();
    const toggle = document.getElementById('app-menu-toggle');
    const drawer = document.getElementById('app-menu-drawer');
    const scrim = document.getElementById('app-menu-scrim');
    if (toggle) {
        const label = isOpen ? t('appMenu.close') : t('appMenu.open');
        toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        toggle.setAttribute('aria-label', label);
        toggle.title = label;
    }
    if (drawer) drawer.hidden = !isOpen;
    if (scrim) scrim.hidden = !isOpen;
}

function setAppMenuOpen(open) {
    document.body?.classList.toggle('app-menu-open', Boolean(open));
    updateAppMenuState();
}

function toggleAppMenu() {
    setAppMenuOpen(!isAppMenuOpen());
}

function closeAppMenu() {
    setAppMenuOpen(false);
}

updateAppMenuState();
document.addEventListener('langchange', updateAppMenuState);

// ─── LANGUAGE TOGGLE ────────────────────────────
// Skrót PL/EN w ustawieniach — przełącza między językami.
function toggleLang() {
    setLang(CURRENT_LANG === 'pl' ? 'en' : 'pl');
}
function updateLangLabel() {
    document.querySelectorAll('.lang-label').forEach(el => {
        el.textContent = CURRENT_LANG === 'pl' ? 'PL' : 'EN';
    });
}
updateLangLabel();
document.addEventListener('langchange', updateLangLabel);

// ─── PARKING COSTS INFO ─────────────────────────
// Mały tabset w modalu informacyjnym, bez zależności od frameworka.
function setParkingCostsTab(tab) {
    const selectedTab = String(tab || 'owner');
    document.querySelectorAll('[data-parking-costs-tab]').forEach(button => {
        const isActive = button.dataset.parkingCostsTab === selectedTab;
        button.classList.toggle('is-active', isActive);
        button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    document.querySelectorAll('[data-parking-costs-panel]').forEach(panel => {
        const isActive = panel.dataset.parkingCostsPanel === selectedTab;
        panel.classList.toggle('is-active', isActive);
        panel.hidden = !isActive;
    });
}

function openParkingCostsModal() {
    setParkingCostsTab('owner');
    openModal('modal-parking-costs');
}

// ─── MODALS (pomoc + ustawienia) ────────────────
// Otwarcie po id; zamykanie kliknięciem w backdrop, ✕, lub ESC.
let pendingConfirmResolve = null;

function openModal(id, options = {}) {
    const modal = document.getElementById(id);
    if (!modal) return;
    const preserveOpen = Boolean(options.preserveOpen);
    if (!preserveOpen) {
        document.querySelectorAll('.modal-backdrop').forEach(m => {
            if (m !== modal) hideModalBackdrop(m);
        });
    }
    modal.hidden = false;
}

function openModalBackdrops() {
    return Array.from(document.querySelectorAll('.modal-backdrop:not([hidden])'));
}

function topOpenModalBackdrop() {
    return openModalBackdrops().at(-1) || null;
}

function hideModalBackdrop(backdrop) {
    if (!(backdrop instanceof Element) || !backdrop.classList.contains('modal-backdrop') || backdrop.hidden) return;
    backdrop.dispatchEvent(new CustomEvent('modalclose', { detail: { id: backdrop.id } }));
    backdrop.hidden = true;
}

function closeModal(target) {
    // target może być: undefined (przycisk ✕), albo elementem backdrop (klik na tło)
    if (target instanceof Element && target.classList.contains('modal-backdrop')) {
        hideModalBackdrop(target);
    } else {
        hideModalBackdrop(topOpenModalBackdrop());
    }
}
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (isAppMenuOpen()) {
            closeAppMenu();
            return;
        }
        const confirmModal = document.getElementById('modal-confirm');
        if (confirmModal && !confirmModal.hidden) {
            closeConfirmModal(false);
            return;
        }
        const adminModal = document.getElementById('modal-admin-login');
        if (adminModal && !adminModal.hidden) {
            closeAdminLoginModal(false);
            return;
        }
        closeModal();
    }
});

function confirmAction({ title, message, confirmLabel } = {}) {
    if (pendingConfirmResolve) {
        pendingConfirmResolve(false);
        pendingConfirmResolve = null;
    }
    return new Promise(resolve => {
        pendingConfirmResolve = resolve;
        const titleEl = document.getElementById('confirm-title');
        const messageEl = document.getElementById('confirm-message');
        const submit = document.getElementById('confirm-submit');
        const cancel = document.getElementById('confirm-cancel');
        if (titleEl) titleEl.textContent = title || t('modal.confirm.title');
        if (messageEl) messageEl.textContent = message || '';
        if (submit) submit.textContent = confirmLabel || t('modal.confirm.confirm');
        if (cancel) cancel.textContent = t('modal.confirm.cancel');
        openModal('modal-confirm', { preserveOpen: true });
        requestAnimationFrame(() => submit?.focus());
    });
}

function closeConfirmModal(confirmed = false, target = null) {
    if (target instanceof Element && !target.classList.contains('modal-backdrop')) return;
    const modal = document.getElementById('modal-confirm');
    if (modal) modal.hidden = true;
    if (pendingConfirmResolve) {
        pendingConfirmResolve(Boolean(confirmed));
        pendingConfirmResolve = null;
    }
}

function submitConfirmAction(event) {
    event.preventDefault();
    closeConfirmModal(true);
}
