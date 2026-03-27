/**
 * API service for communicating with the FastAPI backend.
 * In development, requests are proxied via the "proxy" field in package.json.
 */

export const fetchConfig = async () => {
    const response = await fetch('/api/config');
    if (!response.ok) throw new Error('Failed to load config');
    return response.json();
};

export const extractForm = async (transcript, formType, site) => {
    const response = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript, form_type: formType, site }),
    });

    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Extraction failed');
    }

    return response.json();
};

export const submitForm = async (formType, formData, userUid) => {
    const response = await fetch('/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            form_type: formType,
            form_data: formData,
            user_uid: userUid,
        }),
    });

    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Submit failed');
    }

    return response.json();
};
