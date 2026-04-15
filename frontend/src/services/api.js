/**
 * API service for communicating with the FastAPI backend.
 * In development, requests are proxied via the "proxy" field in package.json.
 */

import { auth } from '../firebase';

const getAuthHeaders = async () => {
    const user = auth.currentUser;
    if (!user) throw new Error('Not authenticated');
    const token = await user.getIdToken();
    return {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
    };
};

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


// ── Monitor / hierarchy APIs ────────────────────────────────────────

export const fetchMe = async () => {
    const headers = await getAuthHeaders();
    const response = await fetch('/api/me', { headers });
    if (!response.ok) throw new Error('Failed to fetch profile');
    return response.json();
};

export const fetchTeam = async (uid) => {
    const headers = await getAuthHeaders();
    const response = await fetch(`/api/team/${uid}`, { headers });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to fetch team');
    }
    return response.json();
};

export const fetchMonitorForms = async (uid) => {
    const headers = await getAuthHeaders();
    const response = await fetch(`/api/monitor/${uid}/forms`, { headers });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to fetch forms');
    }
    return response.json();
};
