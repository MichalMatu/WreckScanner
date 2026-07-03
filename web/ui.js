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
    restoreDraggableModalPosition(modal);
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
        document.querySelectorAll('.modal-backdrop:not([hidden])').forEach(hideModalBackdrop);
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

function modalPositionKey(backdrop) {
    return backdrop?.id ? `${MODAL_POSITION_STORAGE_PREFIX}${backdrop.id}` : null;
}

function shouldCenterDraggableModals() {
    return window.matchMedia('(max-width: 640px), (max-height: 520px)').matches;
}

function clampModalPosition(dialog, left, top) {
    const margin = 8;
    const rect = dialog.getBoundingClientRect();
    const maxLeft = Math.max(margin, window.innerWidth - rect.width - margin);
    const maxTop = Math.max(margin, window.innerHeight - rect.height - margin);
    return {
        left: Math.min(Math.max(margin, left), maxLeft),
        top: Math.min(Math.max(margin, top), maxTop),
    };
}

function setModalPosition(dialog, left, top) {
    const pos = clampModalPosition(dialog, left, top);
    dialog.style.position = 'fixed';
    dialog.style.left = `${pos.left}px`;
    dialog.style.top = `${pos.top}px`;
    dialog.style.right = 'auto';
    dialog.style.margin = '0';
    return pos;
}

function resetModalPosition(dialog) {
    dialog.style.position = '';
    dialog.style.left = '';
    dialog.style.top = '';
    dialog.style.right = '';
    dialog.style.margin = '';
}

function restoreDraggableModalPosition(backdrop) {
    const key = modalPositionKey(backdrop);
    const dialog = backdrop.querySelector('.draggable-modal');
    if (!key || !dialog) return;

    if (shouldCenterDraggableModals()) {
        resetModalPosition(dialog);
        return;
    }

    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(key) || 'null'); } catch (_) {}
    resetModalPosition(dialog);
    if (saved && Number.isFinite(saved.left) && Number.isFinite(saved.top)) {
        requestAnimationFrame(() => setModalPosition(dialog, saved.left, saved.top));
    }
}

function saveDraggableModalPosition(dialog) {
    if (shouldCenterDraggableModals()) return;
    const backdrop = dialog.closest('.modal-backdrop');
    const key = backdrop ? modalPositionKey(backdrop) : null;
    if (!key) return;
    const rect = dialog.getBoundingClientRect();
    try {
        localStorage.setItem(key, JSON.stringify({ left: Math.round(rect.left), top: Math.round(rect.top) }));
    } catch (_) {}
}

let modalDrag = null;
document.querySelectorAll('.draggable-modal .modal-drag-handle').forEach(handle => {
    handle.addEventListener('pointerdown', e => {
        if (e.target.closest('button, input, select, textarea, a')) return;
        const dialog = handle.closest('.draggable-modal');
        if (!dialog) return;
        if (shouldCenterDraggableModals()) return;
        const rect = dialog.getBoundingClientRect();
        modalDrag = {
            dialog,
            startX: e.clientX,
            startY: e.clientY,
            startLeft: rect.left,
            startTop: rect.top,
        };
        dialog.classList.add('is-dragging');
        setModalPosition(dialog, rect.left, rect.top);
        handle.setPointerCapture(e.pointerId);
        e.preventDefault();
    });
});
document.addEventListener('pointermove', e => {
    if (!modalDrag) return;
    setModalPosition(
        modalDrag.dialog,
        modalDrag.startLeft + e.clientX - modalDrag.startX,
        modalDrag.startTop + e.clientY - modalDrag.startY
    );
});
document.addEventListener('pointerup', () => {
    if (!modalDrag) return;
    modalDrag.dialog.classList.remove('is-dragging');
    saveDraggableModalPosition(modalDrag.dialog);
    modalDrag = null;
});
window.addEventListener('resize', () => {
    document.querySelectorAll('.draggable-modal').forEach(dialog => {
        if (dialog.closest('.modal-backdrop')?.hidden) return;
        if (shouldCenterDraggableModals()) {
            resetModalPosition(dialog);
            return;
        }
        if (dialog.style.position !== 'fixed') return;
        const rect = dialog.getBoundingClientRect();
        setModalPosition(dialog, rect.left, rect.top);
    });
});
