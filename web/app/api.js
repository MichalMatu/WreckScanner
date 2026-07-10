class ApiError extends Error {
    constructor(message, { status = 0, requestId = '', payload = null } = {}) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.requestId = requestId;
        this.payload = payload;
    }
}

const API_DEFAULT_TIMEOUT_MS = 20000;
const API_REPORT_TIMEOUT_MS = 120000;

function apiLocalizedText(key, fallback) {
    if (typeof t !== 'function') return fallback;
    const translated = t(key);
    return translated && translated !== key ? translated : fallback;
}

async function apiRequest(url, options, decodeSuccess) {
    const {
        timeoutMs = API_DEFAULT_TIMEOUT_MS,
        handleAdminSession = true,
        signal: callerSignal,
        ...fetchOptions
    } = options;
    const controller = new AbortController();
    let timedOut = false;
    const onCallerAbort = () => controller.abort(callerSignal?.reason);
    if (callerSignal?.aborted) onCallerAbort();
    else callerSignal?.addEventListener('abort', onCallerAbort, { once: true });
    const timeoutId = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
    }, Math.max(1, Number(timeoutMs) || API_DEFAULT_TIMEOUT_MS));
    try {
        const resp = await fetch(url, { ...fetchOptions, signal: controller.signal });
        const data = resp.ok
            ? await decodeSuccess(resp)
            : await resp.json().catch(() => ({}));
        if (!resp.ok) {
            const requestId = data.request_id || resp.headers?.get('X-Request-ID') || '';
            if (resp.status === 401 && handleAdminSession) {
                if (typeof setAdminAuthenticated === 'function') setAdminAuthenticated(false);
                document.dispatchEvent(new CustomEvent('adminsessionexpired'));
            }
            throw new ApiError(data.error || `HTTP ${resp.status}`, {
                status: resp.status,
                requestId,
                payload: data,
            });
        }
        return data;
    } catch (error) {
        if (timedOut) {
            throw new ApiError(
                apiLocalizedText('api.timeout', 'Żądanie przekroczyło limit czasu.'),
                { payload: { code: 'timeout' } },
            );
        }
        if (controller.signal.aborted) {
            throw new ApiError(
                apiLocalizedText('api.cancelled', 'Żądanie zostało anulowane.'),
                { payload: { code: 'cancelled' } },
            );
        }
        if (error instanceof ApiError) throw error;
        throw new ApiError(
            apiLocalizedText('api.offline', 'Nie udało się połączyć z serwerem.'),
            { payload: { code: 'network' } },
        );
    } finally {
        window.clearTimeout(timeoutId);
        callerSignal?.removeEventListener('abort', onCallerAbort);
    }
}

async function apiJson(url, options = {}) {
    return apiRequest(url, options, resp => resp.json().catch(() => ({})));
}

async function apiBlob(url, options = {}) {
    return apiRequest(url, options, resp => resp.blob());
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
