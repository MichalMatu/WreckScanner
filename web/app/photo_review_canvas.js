function drawPhotoReviewCanvas() {
    const canvas = document.getElementById('photo-review-canvas');
    if (!canvas || !photoReviewImage) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const metrics = photoReviewCanvasMetrics(canvas);
    const handleHalfX = (PHOTO_REVIEW_HANDLE_SIZE_PX * metrics.canvasScaleX) / 2;
    const handleHalfY = (PHOTO_REVIEW_HANDLE_SIZE_PX * metrics.canvasScaleY) / 2;
    const centerRadius = PHOTO_REVIEW_CENTER_DOT_SIZE_PX * Math.max(metrics.canvasScaleX, metrics.canvasScaleY);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(photoReviewImage, 0, 0, canvas.width, canvas.height);
    const drawRedaction = (redaction, draft = false, index = -1) => {
        const points = Array.isArray(redaction?.points) ? redaction.points : [];
        if (points.length < 3) return;
        ctx.fillStyle = draft ? 'rgba(250, 204, 21, 0.25)' : 'rgba(15, 23, 42, 0.82)';
        ctx.strokeStyle = draft ? '#facc15' : (index === activePhotoReviewRedactionIndex ? '#f97316' : '#93c5fd');
        ctx.lineWidth = index === activePhotoReviewRedactionIndex ? 3 : 2;
        ctx.beginPath();
        points.forEach((point, pointIndex) => {
            const x = point.x * canvas.width;
            const y = point.y * canvas.height;
            if (pointIndex === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        if (!draft && index === activePhotoReviewRedactionIndex) {
            const center = redactionCenter(redaction);
            ctx.beginPath();
            ctx.arc(center.x * canvas.width, center.y * canvas.height, centerRadius, 0, Math.PI * 2);
            ctx.fillStyle = '#f97316';
            ctx.fill();
            points.forEach(point => {
                const x = point.x * canvas.width;
                const y = point.y * canvas.height;
                ctx.fillStyle = '#fff7ed';
                ctx.strokeStyle = '#f97316';
                ctx.lineWidth = 2;
                ctx.fillRect(x - handleHalfX, y - handleHalfY, handleHalfX * 2, handleHalfY * 2);
                ctx.strokeRect(x - handleHalfX, y - handleHalfY, handleHalfX * 2, handleHalfY * 2);
            });
        }
    };
    photoReviewRedactions.forEach((redaction, index) => drawRedaction(redaction, false, index));
    if (photoReviewDraftRect) drawRedaction(photoReviewDraftRect, true);
    if (typeof updatePhotoReviewCanvasAccessibility === 'function') updatePhotoReviewCanvasAccessibility();
}

const PHOTO_REVIEW_HANDLE_SIZE_PX = 14;
const PHOTO_REVIEW_HANDLE_HIT_RADIUS_PX = 18;
const PHOTO_REVIEW_CENTER_DOT_SIZE_PX = 4;

function photoReviewCanvasMetrics(canvas = document.getElementById('photo-review-canvas')) {
    if (!canvas) {
        return { displayWidth: 1, displayHeight: 1, canvasScaleX: 1, canvasScaleY: 1 };
    }
    const rect = canvas.getBoundingClientRect();
    const displayWidth = Math.max(1, rect.width || canvas.width || 1);
    const displayHeight = Math.max(1, rect.height || canvas.height || 1);
    return {
        rect,
        displayWidth,
        displayHeight,
        canvasScaleX: Math.max(1, canvas.width || 1) / displayWidth,
        canvasScaleY: Math.max(1, canvas.height || 1) / displayHeight,
    };
}

function photoReviewPointer(event) {
    const canvas = document.getElementById('photo-review-canvas');
    if (!canvas) return null;
    const metrics = photoReviewCanvasMetrics(canvas);
    const x = (event.clientX - metrics.rect.left) / metrics.displayWidth;
    const y = (event.clientY - metrics.rect.top) / metrics.displayHeight;
    return {
        x: Math.min(Math.max(x, 0), 1),
        y: Math.min(Math.max(y, 0), 1),
    };
}

function clearPhotoReviewCursorState(canvas = document.getElementById('photo-review-canvas')) {
    if (!canvas) return;
    canvas.classList.remove(
        'is-hovering-handle',
        'is-hovering-redaction',
        'is-drawing-redaction',
        'is-moving-redaction',
        'is-resizing-redaction',
    );
    canvas.style.cursor = '';
}

function setPhotoReviewCursorState(canvas, state, cursor = '') {
    clearPhotoReviewCursorState(canvas);
    if (!canvas || !state) return;
    if (state === 'handle') canvas.classList.add('is-hovering-handle');
    if (state === 'redaction') canvas.classList.add('is-hovering-redaction');
    if (state === 'draw') canvas.classList.add('is-drawing-redaction');
    if (state === 'move') canvas.classList.add('is-moving-redaction');
    if (state === 'resize') canvas.classList.add('is-resizing-redaction');
    canvas.style.cursor = cursor;
}

function capturePhotoReviewPointer(canvas, pointerId) {
    try {
        canvas.setPointerCapture?.(pointerId);
    } catch (_) {
        // Pointer capture can fail when the browser has already cancelled the pointer.
    }
}

function releasePhotoReviewPointer(canvas, pointerId) {
    try {
        canvas.releasePointerCapture?.(pointerId);
    } catch (_) {
        // The pointer may already be released after a cancel/lost-capture event.
    }
}

function clampUnit(value) {
    return Math.min(Math.max(Number(value) || 0, 0), 1);
}

function rectToRedaction(x, y, width, height) {
    x = clampUnit(x);
    y = clampUnit(y);
    width = Math.min(Math.max(Number(width) || 0, 0), 1 - x);
    height = Math.min(Math.max(Number(height) || 0, 0), 1 - y);
    if (width < 0.005 || height < 0.005) return null;
    return {
        points: [
            { x, y },
            { x: x + width, y },
            { x: x + width, y: y + height },
            { x, y: y + height },
        ].map(point => ({ x: Number(point.x.toFixed(6)), y: Number(point.y.toFixed(6)) })),
    };
}

function normalizePhotoReviewRedaction(redaction) {
    if (!redaction || typeof redaction !== 'object') return null;
    if (Array.isArray(redaction.points)) {
        const points = redaction.points
            .map(point => point && typeof point === 'object'
                ? { x: Number(clampUnit(point.x).toFixed(6)), y: Number(clampUnit(point.y).toFixed(6)) }
                : null)
            .filter(Boolean);
        return points.length >= 3 ? { points } : null;
    }
    return rectToRedaction(redaction.x, redaction.y, redaction.width, redaction.height);
}

function normalizeReviewRect(start, end) {
    const x = Math.min(start.x, end.x);
    const y = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);
    return rectToRedaction(x, y, width, height);
}

function redactionCenter(redaction) {
    const points = Array.isArray(redaction?.points) ? redaction.points : [];
    const total = points.reduce((acc, point) => ({ x: acc.x + point.x, y: acc.y + point.y }), { x: 0, y: 0 });
    const count = Math.max(1, points.length);
    return { x: total.x / count, y: total.y / count };
}

function pointInsideRedaction(point, redaction) {
    const points = Array.isArray(redaction?.points) ? redaction.points : [];
    if (points.length < 3) return false;
    let inside = false;
    for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
        const a = points[i];
        const b = points[j];
        const intersects = ((a.y > point.y) !== (b.y > point.y))
            && (point.x < ((b.x - a.x) * (point.y - a.y)) / ((b.y - a.y) || 1e-9) + a.x);
        if (intersects) inside = !inside;
    }
    return inside;
}

function selectPhotoRedactionAt(point) {
    for (let index = photoReviewRedactions.length - 1; index >= 0; index--) {
        if (pointInsideRedaction(point, photoReviewRedactions[index])) {
            activePhotoReviewRedactionIndex = index;
            drawPhotoReviewCanvas();
            return true;
        }
    }
    activePhotoReviewRedactionIndex = -1;
    drawPhotoReviewCanvas();
    return false;
}

function redactionAtPoint(point) {
    for (let index = photoReviewRedactions.length - 1; index >= 0; index--) {
        if (pointInsideRedaction(point, photoReviewRedactions[index])) return index;
    }
    return -1;
}

function photoReviewHandleCursor(redaction, pointIndex) {
    const point = redaction?.points?.[pointIndex];
    if (!point) return 'grab';
    const center = redactionCenter(redaction);
    return (point.x - center.x) * (point.y - center.y) >= 0 ? 'nwse-resize' : 'nesw-resize';
}

function redactionHandleAtPoint(point, redactionIndex = activePhotoReviewRedactionIndex) {
    if (!point || redactionIndex < 0) return null;
    const redaction = photoReviewRedactions[redactionIndex];
    const points = redaction?.points || [];
    const metrics = photoReviewCanvasMetrics();
    for (let pointIndex = 0; pointIndex < points.length; pointIndex++) {
        const candidate = points[pointIndex];
        const dx = (candidate.x - point.x) * metrics.displayWidth;
        const dy = (candidate.y - point.y) * metrics.displayHeight;
        if (Math.hypot(dx, dy) <= PHOTO_REVIEW_HANDLE_HIT_RADIUS_PX) {
            return {
                redactionIndex,
                pointIndex,
                cursor: photoReviewHandleCursor(redaction, pointIndex),
            };
        }
    }
    return null;
}

function resizeRedactionPoint(redaction, pointIndex, point) {
    const points = Array.isArray(redaction?.points) ? redaction.points : [];
    if (pointIndex < 0 || pointIndex >= points.length) return redaction;
    return {
        points: points.map((candidate, index) => (
            index === pointIndex
                ? { x: Number(clampUnit(point.x).toFixed(6)), y: Number(clampUnit(point.y).toFixed(6)) }
                : candidate
        )),
    };
}

function moveRedaction(redaction, dx, dy) {
    const points = Array.isArray(redaction?.points) ? redaction.points : [];
    if (!points.length) return redaction;
    const minX = Math.min(...points.map(point => point.x));
    const maxX = Math.max(...points.map(point => point.x));
    const minY = Math.min(...points.map(point => point.y));
    const maxY = Math.max(...points.map(point => point.y));
    const safeDx = Math.min(Math.max(dx, -minX), 1 - maxX);
    const safeDy = Math.min(Math.max(dy, -minY), 1 - maxY);
    return {
        points: points.map(point => ({
            x: Number(clampUnit(point.x + safeDx).toFixed(6)),
            y: Number(clampUnit(point.y + safeDy).toFixed(6)),
        })),
    };
}

function scaleRedaction(redaction, amount) {
    const points = Array.isArray(redaction?.points) ? redaction.points : [];
    if (points.length < 3) return redaction;
    const center = redactionCenter(redaction);
    const factor = Math.max(0.2, 1 + amount);
    return {
        points: points.map(point => ({
            x: Number(clampUnit(center.x + (point.x - center.x) * factor).toFixed(6)),
            y: Number(clampUnit(center.y + (point.y - center.y) * factor).toFixed(6)),
        })),
    };
}

function photoReviewCanvasText(key, fallback, params = null) {
    if (typeof t !== 'function') return fallback;
    const translated = t(key, params || undefined);
    return translated && translated !== key ? translated : fallback;
}

function updatePhotoReviewCanvasAccessibility() {
    const canvas = document.getElementById('photo-review-canvas');
    const status = document.getElementById('photo-review-canvas-status');
    if (!canvas) return;
    const count = photoReviewRedactions.length;
    const selected = activePhotoReviewRedactionIndex >= 0 ? activePhotoReviewRedactionIndex + 1 : 0;
    const label = photoReviewCanvasText(
        'modal.photoReview.canvasState',
        `Anonimizacja zdjęcia. Obszary: ${count}. Wybrany: ${selected || 'brak'}.`,
        { count, selected: selected || '-' },
    );
    canvas.setAttribute('aria-label', label);
    if (status) status.textContent = label;
}

function undoPhotoRedaction() {
    if (!photoReviewRedactions.length) return;
    photoReviewRedactions.pop();
    activePhotoReviewRedactionIndex = photoReviewRedactions.length ? photoReviewRedactions.length - 1 : -1;
    drawPhotoReviewCanvas();
}

function rotatePhotoRedaction(degrees) {
    if (!photoReviewRedactions.length) return;
    if (activePhotoReviewRedactionIndex < 0) {
        activePhotoReviewRedactionIndex = photoReviewRedactions.length - 1;
    }
    const redaction = photoReviewRedactions[activePhotoReviewRedactionIndex];
    if (!redaction?.points?.length) return;
    const center = redactionCenter(redaction);
    const radians = (Number(degrees) || 0) * Math.PI / 180;
    const cos = Math.cos(radians);
    const sin = Math.sin(radians);
    photoReviewRedactions[activePhotoReviewRedactionIndex] = {
        points: redaction.points.map(point => {
            const dx = point.x - center.x;
            const dy = point.y - center.y;
            return {
                x: Number(clampUnit(center.x + dx * cos - dy * sin).toFixed(6)),
                y: Number(clampUnit(center.y + dx * sin + dy * cos).toFixed(6)),
            };
        }),
    };
    drawPhotoReviewCanvas();
}

(() => {
    const canvas = document.getElementById('photo-review-canvas');
    if (!canvas) return;
    canvas.tabIndex = 0;
    canvas.setAttribute('role', 'application');
    canvas.setAttribute('aria-describedby', 'photo-review-canvas-help');
    const help = document.createElement('p');
    help.id = 'photo-review-canvas-help';
    help.className = 'visually-hidden';
    help.textContent = photoReviewCanvasText(
        'modal.photoReview.canvasHelp',
        'Enter dodaje obszar. Strzałki przesuwają, Control i strzałki zmieniają rozmiar, Delete usuwa, Page Up i Page Down wybierają obszar.',
    );
    const accessibilityStatus = document.createElement('p');
    accessibilityStatus.id = 'photo-review-canvas-status';
    accessibilityStatus.className = 'visually-hidden';
    accessibilityStatus.setAttribute('role', 'status');
    accessibilityStatus.setAttribute('aria-live', 'polite');
    canvas.after(help, accessibilityStatus);
    updatePhotoReviewCanvasAccessibility();
    let dragState = null;

    canvas.addEventListener('keydown', event => {
        if (!photoReviewImage) return;
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            if (photoReviewRedactions.length >= 100) return;
            const redaction = rectToRedaction(0.35, 0.4, 0.3, 0.2);
            if (!redaction) return;
            photoReviewRedactions.push(redaction);
            activePhotoReviewRedactionIndex = photoReviewRedactions.length - 1;
            drawPhotoReviewCanvas();
            return;
        }
        if (event.key === 'PageUp' || event.key === 'PageDown') {
            if (!photoReviewRedactions.length) return;
            event.preventDefault();
            const delta = event.key === 'PageDown' ? 1 : -1;
            activePhotoReviewRedactionIndex = (
                activePhotoReviewRedactionIndex + delta + photoReviewRedactions.length
            ) % photoReviewRedactions.length;
            drawPhotoReviewCanvas();
            return;
        }
        if ((event.key === 'Delete' || event.key === 'Backspace') && activePhotoReviewRedactionIndex >= 0) {
            event.preventDefault();
            photoReviewRedactions.splice(activePhotoReviewRedactionIndex, 1);
            activePhotoReviewRedactionIndex = Math.min(
                activePhotoReviewRedactionIndex,
                photoReviewRedactions.length - 1,
            );
            drawPhotoReviewCanvas();
            return;
        }
        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
        if (activePhotoReviewRedactionIndex < 0) return;
        event.preventDefault();
        const step = event.shiftKey ? 0.03 : 0.01;
        const active = photoReviewRedactions[activePhotoReviewRedactionIndex];
        if (event.ctrlKey || event.metaKey) {
            const grow = event.key === 'ArrowRight' || event.key === 'ArrowDown';
            photoReviewRedactions[activePhotoReviewRedactionIndex] = scaleRedaction(active, grow ? step : -step);
        } else {
            const dx = event.key === 'ArrowLeft' ? -step : (event.key === 'ArrowRight' ? step : 0);
            const dy = event.key === 'ArrowUp' ? -step : (event.key === 'ArrowDown' ? step : 0);
            photoReviewRedactions[activePhotoReviewRedactionIndex] = moveRedaction(active, dx, dy);
        }
        drawPhotoReviewCanvas();
    });

    const updateHoverState = event => {
        if (!photoReviewImage) return;
        const point = photoReviewPointer(event);
        const handle = redactionHandleAtPoint(point);
        if (handle) {
            setPhotoReviewCursorState(canvas, 'handle', handle.cursor);
            return;
        }
        const hitIndex = redactionAtPoint(point);
        if (hitIndex >= 0) {
            setPhotoReviewCursorState(canvas, 'redaction');
            return;
        }
        setPhotoReviewCursorState(canvas, 'draw');
    };

    canvas.addEventListener('pointerdown', event => {
        if (!photoReviewImage) return;
        event.preventDefault();
        const start = photoReviewPointer(event);
        if (!start) return;
        const activeHandle = redactionHandleAtPoint(start);
        if (activeHandle) {
            activePhotoReviewRedactionIndex = activeHandle.redactionIndex;
            dragState = {
                pointerId: event.pointerId,
                mode: 'resize',
                start,
                lastPoint: start,
                moved: false,
                activeHandle,
            };
            photoReviewDrawing = false;
            setPhotoReviewCursorState(canvas, 'resize', activeHandle.cursor);
            capturePhotoReviewPointer(canvas, event.pointerId);
            drawPhotoReviewCanvas();
            return;
        }
        const hitIndex = redactionAtPoint(start);
        if (hitIndex >= 0) {
            activePhotoReviewRedactionIndex = hitIndex;
            dragState = {
                pointerId: event.pointerId,
                mode: 'move',
                start,
                lastPoint: start,
                moved: false,
            };
            photoReviewDrawing = false;
            setPhotoReviewCursorState(canvas, 'move');
            capturePhotoReviewPointer(canvas, event.pointerId);
            drawPhotoReviewCanvas();
            return;
        }
        activePhotoReviewRedactionIndex = -1;
        dragState = {
            pointerId: event.pointerId,
            mode: 'draw',
            start,
            lastPoint: start,
            moved: false,
        };
        photoReviewDrawing = true;
        setPhotoReviewCursorState(canvas, 'draw');
        capturePhotoReviewPointer(canvas, event.pointerId);
    });

    canvas.addEventListener('pointermove', event => {
        if (!photoReviewImage) return;
        if (!dragState) {
            updateHoverState(event);
            return;
        }
        if (event.pointerId !== dragState.pointerId) return;
        event.preventDefault();
        const current = photoReviewPointer(event);
        if (!current) return;
        const distance = Math.hypot(current.x - dragState.start.x, current.y - dragState.start.y);
        dragState.moved = dragState.moved || distance > 0.003;
        if (dragState.mode === 'move' && activePhotoReviewRedactionIndex >= 0 && dragState.lastPoint) {
            const dx = current.x - dragState.lastPoint.x;
            const dy = current.y - dragState.lastPoint.y;
            photoReviewRedactions[activePhotoReviewRedactionIndex] = moveRedaction(
                photoReviewRedactions[activePhotoReviewRedactionIndex],
                dx,
                dy,
            );
            dragState.lastPoint = current;
        } else if (dragState.mode === 'resize' && dragState.activeHandle) {
            photoReviewRedactions[dragState.activeHandle.redactionIndex] = resizeRedactionPoint(
                photoReviewRedactions[dragState.activeHandle.redactionIndex],
                dragState.activeHandle.pointIndex,
                current,
            );
        } else if (dragState.mode === 'draw') {
            photoReviewDraftRect = normalizeReviewRect(dragState.start, current);
        }
        drawPhotoReviewCanvas();
    });

    const finishDrag = event => {
        if (!dragState || event.pointerId !== dragState.pointerId) return;
        event.preventDefault();
        const end = photoReviewPointer(event);
        const rect = dragState.mode === 'draw' && end ? normalizeReviewRect(dragState.start, end) : null;
        if (dragState.mode === 'draw' && rect) {
            photoReviewRedactions.push(rect);
            activePhotoReviewRedactionIndex = photoReviewRedactions.length - 1;
        } else if (!dragState.moved && end) {
            selectPhotoRedactionAt(end);
        }
        releasePhotoReviewPointer(canvas, event.pointerId);
        photoReviewDraftRect = null;
        photoReviewDrawing = false;
        dragState = null;
        drawPhotoReviewCanvas();
        if (end) updateHoverState(event);
        else clearPhotoReviewCursorState(canvas);
    };

    canvas.addEventListener('pointerup', finishDrag);
    canvas.addEventListener('pointercancel', event => {
        if (!dragState || event.pointerId !== dragState.pointerId) return;
        releasePhotoReviewPointer(canvas, event.pointerId);
        photoReviewDraftRect = null;
        photoReviewDrawing = false;
        dragState = null;
        clearPhotoReviewCursorState(canvas);
        drawPhotoReviewCanvas();
    });
    canvas.addEventListener('pointerleave', () => {
        if (!dragState) clearPhotoReviewCursorState(canvas);
    });
})();
