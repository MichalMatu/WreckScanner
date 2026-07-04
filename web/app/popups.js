const MAP_POPUP_LEAFLET_OPTIONS = Object.freeze({ maxWidth: 540 });

function mapPopupOptions() {
    return { ...MAP_POPUP_LEAFLET_OPTIONS };
}

function mapPopupClasses(modifiers = []) {
    const modifierList = Array.isArray(modifiers) ? modifiers : [modifiers];
    const classes = ['map-popup'];
    modifierList.forEach(modifier => {
        String(modifier || '').trim().split(/\s+/).forEach(className => {
            if (className) classes.push(className);
        });
    });
    return classes.join(' ');
}

function mapPopup(content, modifiers = []) {
    return `<div class="${escapeHtml(mapPopupClasses(modifiers))}">${content}</div>`;
}

function popupCompactLink(href, label, title) {
    if (!href) return '';
    return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener" title="${escapeHtml(title || label)}">${escapeHtml(label)}</a>`;
}

function popupHeader(title, value = '') {
    const valueHtml = value ? `<span>${escapeHtml(value)}</span>` : '';
    return `
        <div class="map-popup-head">
            <strong>${escapeHtml(title)}</strong>
            ${valueHtml}
        </div>
    `;
}

function popupMeta(parts) {
    const items = (parts || []).filter(part => part !== undefined && part !== null && String(part).trim() !== '');
    if (!items.length) return '';
    return `<div class="map-popup-meta">${items.map(part => `<span>${escapeHtml(part)}</span>`).join('')}</div>`;
}

function popupLinks(links) {
    const items = (links || []).filter(Boolean);
    if (!items.length) return '';
    return `
        <div class="map-popup-links">
            ${items.map(link => `<span class="map-popup-link-item">${link}</span>`).join('')}
        </div>
    `;
}

function popupActions(actions) {
    const html = (actions || []).filter(Boolean).join('');
    return html ? `<div class="map-popup-actions">${html}</div>` : '';
}

function humanDatePartsFromPhotoText(value) {
    const text = String(value || '').trim();
    const match = text.match(/(20\d{2})[-_:.]?([01]\d)[-_:.]?([0-3]\d)(?:[T _.-]?([0-2]\d)[:_.-]?([0-5]\d))?/);
    if (!match) return null;
    const [, year, month, day, hour, minute] = match;
    const date = `${day}.${month}.${year}`;
    return {
        date,
        dateTime: `${date}${hour && minute ? `, ${hour}:${minute}` : ''}`,
    };
}

function humanNameFromFilename(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    const base = raw.split(/[\\/]/).pop().replace(/\.[A-Za-z0-9]{1,5}$/, '');
    const cleaned = base.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
    if (!cleaned || /^\d+$/.test(cleaned)) return '';
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function photoPreviewDisplay(photo, index = 0) {
    const source = String(photo?.source || '');
    const rawLabel = String(photo?.label || '').trim();
    const detail = rawLabel;
    const year = rawLabel.match(/^(?:19|20)\d{2}$/)?.[0] || '';
    if ((source === 'evidence' || source === 'inspect') && year) {
        return {
            name: t('modal.photoPreview.mapCropYear', { year }),
            badge: year,
            detail,
        };
    }
    const humanDate = humanDatePartsFromPhotoText(rawLabel);
    if (humanDate) {
        return {
            name: t('modal.photoPreview.photoDated', { date: humanDate.dateTime }),
            badge: humanDate.date,
            detail,
        };
    }
    const humanName = humanNameFromFilename(rawLabel);
    return {
        name: humanName || t('modal.photoPreview.photoNumber', { n: index + 1 }),
        detail,
    };
}

function photoPreviewGalleryItems(previews) {
    return Array.isArray(previews)
        ? previews.filter(photo => photo && photo.public_thumb).map((photo, index) => {
            const display = photoPreviewDisplay(photo, index);
            return {
                url: String(photo.public_image || photo.public_thumb || ''),
                thumb: String(photo.public_thumb || ''),
                title: String(display.name || ''),
                badge: String(display.badge || display.name || ''),
                detail: String(display.detail || ''),
            };
        }).filter(item => item.url && item.thumb)
        : [];
}

function popupVisiblePhotoCount(previews, { max = MAP_POPUP_PREVIEW_MAX_IMAGES } = {}) {
    const maxItems = Number.isFinite(Number(max)) ? Math.max(0, Number(max)) : MAP_POPUP_PREVIEW_MAX_IMAGES;
    return Math.min(photoPreviewGalleryItems(previews).length, maxItems);
}

function popupPhotoCountToken(count) {
    const numericCount = Math.max(0, Math.floor(Number(count) || 0));
    return numericCount >= 5 ? 'many' : String(numericCount);
}

function mapPopupMediaModifiers(previews, modifiers = [], options = {}) {
    return [
        'map-popup--media',
        `map-popup--media-count-${popupPhotoCountToken(popupVisiblePhotoCount(previews, options))}`,
        ...(Array.isArray(modifiers) ? modifiers : [modifiers]).filter(Boolean),
    ];
}

function popupPhotoGrid(previews, { className = '', max = MAP_POPUP_PREVIEW_MAX_IMAGES } = {}) {
    const maxItems = Number.isFinite(Number(max)) ? Math.max(0, Number(max)) : MAP_POPUP_PREVIEW_MAX_IMAGES;
    const galleryItems = photoPreviewGalleryItems(previews);
    const photos = galleryItems.slice(0, maxItems);
    if (!photos.length) return '';
    const classAttr = [
        'map-popup-photo-grid',
        `map-popup-photo-grid--count-${popupPhotoCountToken(photos.length)}`,
        className,
    ].filter(Boolean).join(' ');
    const galleryAttr = escapeHtml(JSON.stringify(galleryItems.map(item => ({
        url: item.url,
        title: item.title,
        badge: item.badge,
        detail: item.detail,
    }))));
    return `
        <div class="${classAttr}" data-photo-gallery="${galleryAttr}">
            ${photos.map((photo, index) => {
                const thumbUrl = escapeHtml(photo.thumb || '');
                const publicUrl = escapeHtml(photo.url || '');
                const label = escapeHtml(photo.title || '');
                const badge = escapeHtml(photo.badge || photo.title || '');
                const detail = escapeHtml(photo.detail || '');
                return `
                    <button type="button" class="map-popup-photo" data-photo-preview-url="${publicUrl}" data-photo-preview-title="${label}" data-photo-preview-detail="${detail}" data-photo-gallery-index="${index}" title="${detail || label}" aria-label="${label || escapeHtml(t('modal.photoPreview.title'))}">
                        <img src="${thumbUrl}" loading="lazy" alt="">
                        ${badge ? `<span>${badge}</span>` : ''}
                    </button>
                `;
            }).join('')}
        </div>
    `;
}

let photoPreviewGallery = [];
let photoPreviewIndex = 0;

function renderPhotoPreviewModal() {
    const item = photoPreviewGallery[photoPreviewIndex] || null;
    if (!item?.url) return;
    const titleText = String(item.title || t('modal.photoPreview.title'));
    const detailText = String(item.detail || '');
    const titleEl = document.getElementById('photo-preview-title');
    const imageEl = document.getElementById('photo-preview-image');
    const downloadEl = document.getElementById('photo-preview-download');
    const detailEl = document.getElementById('photo-preview-detail');
    const counterEl = document.getElementById('photo-preview-counter');
    const prevButton = document.getElementById('photo-preview-prev');
    const nextButton = document.getElementById('photo-preview-next');
    if (titleEl) titleEl.textContent = titleText;
    if (imageEl) {
        imageEl.alt = titleText;
        imageEl.src = item.url;
    }
    if (downloadEl) {
        downloadEl.href = item.url;
        downloadEl.download = '';
    }
    if (detailEl) {
        detailEl.textContent = detailText;
        detailEl.hidden = !detailText || detailText === titleText;
    }
    if (counterEl) {
        counterEl.textContent = `${photoPreviewIndex + 1}/${photoPreviewGallery.length}`;
        counterEl.hidden = photoPreviewGallery.length <= 1;
    }
    [prevButton, nextButton].forEach(button => {
        if (button) button.disabled = photoPreviewGallery.length <= 1;
    });
}

function openPhotoPreviewModal(url, title = '', gallery = null, index = 0) {
    const fallbackUrl = String(url || '');
    const items = Array.isArray(gallery) && gallery.length
        ? gallery
        : [{ url: fallbackUrl, title: String(title || ''), detail: '' }];
    photoPreviewGallery = items.filter(item => item?.url);
    if (!photoPreviewGallery.length) return;
    photoPreviewIndex = Math.min(Math.max(0, Number(index) || 0), photoPreviewGallery.length - 1);
    renderPhotoPreviewModal();
    openModal('modal-photo-preview', { preserveOpen: true });
}

function movePhotoPreview(delta) {
    if (photoPreviewGallery.length <= 1) return;
    photoPreviewIndex = (photoPreviewIndex + delta + photoPreviewGallery.length) % photoPreviewGallery.length;
    renderPhotoPreviewModal();
}

function photoPreviewGalleryFromButton(activeButton) {
    const grid = activeButton.closest('.map-popup-photo-grid');
    if (grid?.dataset.photoGallery) {
        try {
            const items = JSON.parse(grid.dataset.photoGallery)
                .map(item => ({
                    url: String(item?.url || ''),
                    title: String(item?.title || ''),
                    detail: String(item?.detail || ''),
                }))
                .filter(item => item.url);
            if (items.length) {
                const rawIndex = Number(activeButton.dataset.photoGalleryIndex);
                const activeIndex = Number.isFinite(rawIndex)
                    ? Math.min(Math.max(0, rawIndex), items.length - 1)
                    : 0;
                return { items, activeIndex };
            }
        } catch (_) {}
    }
    const buttons = Array.from(grid?.querySelectorAll('[data-photo-preview-url]') || [activeButton]);
    const items = [];
    let activeIndex = 0;
    buttons.forEach(button => {
        const url = button.dataset.photoPreviewUrl || '';
        if (!url) return;
        if (button === activeButton) activeIndex = items.length;
        items.push({
            url,
            title: button.dataset.photoPreviewTitle || '',
            detail: button.dataset.photoPreviewDetail || '',
        });
    });
    return { items, activeIndex };
}

document.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return;
    const button = event.target.closest('[data-photo-preview-url]');
    if (!button) return;
    event.preventDefault();
    const { items, activeIndex } = photoPreviewGalleryFromButton(button);
    openPhotoPreviewModal(button.dataset.photoPreviewUrl, button.dataset.photoPreviewTitle, items, activeIndex);
});

document.addEventListener('keydown', event => {
    const modal = document.getElementById('modal-photo-preview');
    if (!modal || modal.hidden) return;
    if (event.key === 'ArrowLeft') {
        event.preventDefault();
        movePhotoPreview(-1);
    } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        movePhotoPreview(1);
    }
});

document.getElementById('modal-photo-preview')?.addEventListener('modalclose', () => {
    const imageEl = document.getElementById('photo-preview-image');
    if (imageEl) imageEl.removeAttribute('src');
    photoPreviewGallery = [];
    photoPreviewIndex = 0;
});

function popupPhotoSection(title, previews, options = {}) {
    const { total = null, showHeader = true, ...gridOptions } = options || {};
    const grid = popupPhotoGrid(previews, gridOptions);
    if (!grid) return '';
    const maxItems = Number.isFinite(Number(gridOptions.max))
        ? Math.max(0, Number(gridOptions.max))
        : MAP_POPUP_PREVIEW_MAX_IMAGES;
    const available = Array.isArray(previews)
        ? previews.filter(photo => photo && photo.public_thumb).length
        : 0;
    const visibleCount = Math.min(available, maxItems);
    const numericTotal = Number(total);
    const totalCount = Number.isFinite(numericTotal) && numericTotal > 0 ? numericTotal : available;
    const countText = totalCount > visibleCount ? `${visibleCount}/${totalCount}` : String(totalCount);
    const header = showHeader ? `
        <div class="map-popup-section-title">
            <span>${escapeHtml(title)}</span>
            <span class="map-popup-section-count">${escapeHtml(countText)}</span>
        </div>
    ` : '';
    return `
        <section class="map-popup-photo-section">
            ${header}
            ${grid}
        </section>
    `;
}

function mapPopupIconAction(className, title, onclick, path) {
    return `
        <button type="button" class="map-popup-action ${className}" title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}" onclick="${onclick}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>
        </button>
    `;
}
