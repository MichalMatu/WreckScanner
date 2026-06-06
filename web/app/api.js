class ApiError extends Error {
    constructor(message, { status = 0, requestId = '', payload = null } = {}) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.requestId = requestId;
        this.payload = payload;
    }
}

async function apiJson(url, options = {}) {
    const resp = await fetch(url, options);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        const requestId = data.request_id || resp.headers?.get('X-Request-ID') || '';
        throw new ApiError(data.error || `HTTP ${resp.status}`, {
            status: resp.status,
            requestId,
            payload: data,
        });
    }
    return data;
}

async function apiPostJson(url, payload, options = {}) {
    return apiJson(url, {
        ...options,
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
        body: JSON.stringify(payload),
    });
}

async function apiPatchJson(url, payload, options = {}) {
    return apiJson(url, {
        ...options,
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
        body: JSON.stringify(payload),
    });
}

async function apiDeleteJson(url, options = {}) {
    return apiJson(url, {
        ...options,
        method: 'DELETE',
    });
}

function apiErrorMessage(error, fallback) {
    const message = error?.message || fallback;
    return error?.requestId ? `${message} (${error.requestId})` : message;
}
