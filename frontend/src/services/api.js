/**
 * API service for communicating with the FastAPI backend.
 * In development, requests are proxied via the "proxy" field in package.json.
 * In production, set REACT_APP_API_BASE_URL at build time to point at the
 * deployed backend (e.g. https://streetkind-api.duckdns.org).
 */

import { auth } from '../firebase';

const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/$/, '');

const apiUrl = (path) => `${API_BASE_URL}${path}`;

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
    const response = await fetch(apiUrl('/api/config'));
    if (!response.ok) throw new Error('Failed to load config');
    return response.json();
};

export const extractForm = async (transcript, formType, site) => {
    const response = await fetch(apiUrl('/api/extract'), {
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

export const submitForm = async (formType, formData, status = 'completed') => {
    const headers = await getAuthHeaders();
    const response = await fetch(apiUrl('/api/submit'), {
        method: 'POST',
        headers,
        body: JSON.stringify({
            form_type: formType,
            form_data: formData,
            status,
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
    const response = await fetch(apiUrl('/api/me'), { headers });
    if (!response.ok) throw new Error('Failed to fetch profile');
    return response.json();
};

export const fetchTeam = async (uid) => {
    const headers = await getAuthHeaders();
    const response = await fetch(apiUrl(`/api/team/${uid}`), { headers });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to fetch team');
    }
    return response.json();
};

export const fetchMonitorForms = async (uid) => {
    const headers = await getAuthHeaders();
    const response = await fetch(apiUrl(`/api/monitor/${uid}/forms`), { headers });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to fetch forms');
    }
    return response.json();
};


// ── Incident CRUD (view / edit / delete) ────────────────────────────

export const fetchIncidentFull = async (formId) => {
    const headers = await getAuthHeaders();
    const response = await fetch(apiUrl(`/api/forms/incident/${formId}`), { headers });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to fetch incident');
    }
    return response.json();
};

export const updateIncident = async (formId, formData, status = 'completed') => {
    const headers = await getAuthHeaders();
    const response = await fetch(apiUrl(`/api/forms/incident/${formId}`), {
        method: 'PUT',
        headers,
        body: JSON.stringify({ form_data: formData, status }),
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to update incident');
    }
    return response.json();
};

export const deleteIncident = async (formId) => {
    const headers = await getAuthHeaders();
    const response = await fetch(apiUrl(`/api/forms/incident/${formId}`), {
        method: 'DELETE',
        headers,
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to delete incident');
    }
    return response.json();
};


// ── Transcripts + audio ─────────────────────────────────────────────

export const fetchIncidentTranscripts = async (formId) => {
    const headers = await getAuthHeaders();
    const response = await fetch(apiUrl(`/api/forms/incident/${formId}/transcripts`), { headers });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to fetch transcripts');
    }
    return response.json();
};

export const createTranscript = async (formId, text, audioDurationMs, extractionMeta) => {
    const headers = await getAuthHeaders();
    const response = await fetch(apiUrl(`/api/forms/incident/${formId}/transcripts`), {
        method: 'POST',
        headers,
        body: JSON.stringify({
            text,
            audioDurationMs: audioDurationMs || 0,
            extractionMeta: extractionMeta || null,
        }),
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to create transcript');
    }
    return response.json();
};

export const uploadTranscriptAudio = async (formId, transcriptId, audioBlob) => {
    const user = auth.currentUser;
    if (!user) throw new Error('Not authenticated');
    const token = await user.getIdToken();

    const formData = new FormData();
    formData.append('audio', audioBlob, `transcript.${audioBlob.type.includes('mp4') ? 'm4a' : 'webm'}`);

    const response = await fetch(
        apiUrl(`/api/forms/incident/${formId}/transcripts/${transcriptId}/audio`),
        {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
            body: formData,
        },
    );
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to upload audio');
    }
    return response.json();
};
