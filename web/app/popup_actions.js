function encodedPopupActionCall(actionCall) {
    return encodeURIComponent(String(actionCall || ''));
}

function decodedPopupActionCall(button) {
    try {
        return decodeURIComponent(button?.dataset?.popupActionCall || '');
    } catch (_) {
        return '';
    }
}

mapPopupIconAction = function mapPopupIconAction(className, title, actionCall, path) {
    const encodedAction = escapeHtml(encodedPopupActionCall(actionCall));
    return `
        <button type="button" class="map-popup-action ${className}" title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}" data-popup-action-call="${encodedAction}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>
        </button>
    `;
};

function handlePopupStringAction(call, button) {
    let match = call.match(/^openFieldPhotoOwnerEditor\('([^']*)'\)$/);
    if (match) {
        openFieldPhotoOwnerEditor(match[1]);
        return true;
    }

    match = call.match(/^openPhotoReviewForFieldPhotoGroup\('([^']*)'\)$/);
    if (match) {
        openPhotoReviewForFieldPhotoGroup(match[1]);
        return true;
    }

    match = call.match(/^deleteFieldPhotoGroup\('([^']*)', this\)$/);
    if (match) {
        deleteFieldPhotoGroup(match[1], button);
        return true;
    }

    match = call.match(/^rejectFieldPhotoGroup\('([^']*)', this\)$/);
    if (match) {
        rejectFieldPhotoGroup(match[1], button);
        return true;
    }

    match = call.match(/^updateFieldPhotoGroupResolution\('([^']*)', '(active|removed)', this\)$/);
    if (match) {
        updateFieldPhotoGroupResolution(match[1], match[2], button);
        return true;
    }

    match = call.match(/^openFieldPhotoGroupReport\((-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), '([^']*)', this\)$/);
    if (match) {
        openFieldPhotoGroupReport(Number(match[1]), Number(match[2]), match[3], button);
        return true;
    }

    match = call.match(
        /^openFieldPhotoGroupPhotoUpload\((-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), '([^']*)', '([^']*)', this\)$/
    );
    if (match) {
        openFieldPhotoGroupPhotoUpload(Number(match[1]), Number(match[2]), match[3], match[4], button);
        return true;
    }

    return false;
}

document.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return;
    const button = event.target.closest('[data-popup-action-call]');
    if (!button) return;
    const call = decodedPopupActionCall(button);
    if (!call || !handlePopupStringAction(call, button)) return;
    event.preventDefault();
    event.stopPropagation();
});
