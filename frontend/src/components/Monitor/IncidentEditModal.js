import React, { useCallback, useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Button, Divider, Header, Icon, Label, Loader, Message, Modal, Segment } from 'semantic-ui-react';

import {
    deleteTranscript,
    fetchIncidentFull,
    fetchIncidentTranscripts,
    updateIncident,
} from '../../services/api';
import { persistTranscripts } from '../../services/persistTranscripts';
import { validateIncidentForm } from '../../utils/validators/clientValidators';
import { useAuth } from '../../context/AuthContext';
import IncidentForm from '../forms/IncidentForm';
import VoiceInput from '../VoiceInput';

const EMPTY_ERRORS = { incident: {}, clients: [] };

/** Scroll the first invalid field into view once the error classes render. */
const scrollToFirstError = () => {
    setTimeout(() => {
        const el = document.querySelector('.field.error, .ui.form .error');
        if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
};

const formatDate = (ms) => {
    if (!ms) return '';
    try { return new Date(ms).toLocaleString(); } catch (e) { return ''; }
};

const formatDuration = (ms) => {
    if (!ms || ms < 0) return '';
    const s = Math.round(ms / 1000);
    const mm = Math.floor(s / 60);
    const ss = (s % 60).toString().padStart(2, '0');
    return `${mm}:${ss}`;
};

const TranscriptPanel = ({ transcripts, isAdmin, deletingId, onDelete }) => {
    if (!transcripts || transcripts.length === 0) {
        return (
            <Segment basic>
                <Message info size='small'>
                    <Icon name='microphone slash' />
                    No voice transcripts were recorded for this incident.
                </Message>
            </Segment>
        );
    }

    return (
        <Segment basic>
            {transcripts.map((t, idx) => (
                <Segment key={t.id} secondary>
                    <Header as='h5' style={{ marginBottom: '0.4rem' }}>
                        <Icon name='microphone' color='blue' />
                        Transcript {idx + 1}
                        {t.createdDate && (
                            <Label size='tiny' style={{ marginLeft: '0.6rem' }}>
                                {formatDate(t.createdDate)}
                            </Label>
                        )}
                        {t.audioDurationMs > 0 && (
                            <Label size='tiny'>{formatDuration(t.audioDurationMs)}</Label>
                        )}
                    </Header>
                    {t.audioUrl ? (
                        <audio controls src={t.audioUrl} style={{ width: '100%', marginBottom: '0.5rem' }} />
                    ) : t.audioPath ? (
                        <Message warning size='tiny' style={{ marginBottom: '0.5rem' }}>
                            <Icon name='warning sign' />
                            Audio file recorded but cannot be loaded right now (signed URL expired or storage unreachable). Reopen the incident to retry.
                        </Message>
                    ) : null}
                    <p style={{ whiteSpace: 'pre-wrap', marginTop: '0.3rem' }}>{t.text}</p>
                    {t.extractionMeta && (t.extractionMeta.model || t.extractionMeta.latencyMs) && (
                        <div style={{ fontSize: '0.75rem', color: '#888' }}>
                            {t.extractionMeta.model && <span>Model: {t.extractionMeta.model}  </span>}
                            {t.extractionMeta.latencyMs > 0 && <span>Latency: {t.extractionMeta.latencyMs}ms</span>}
                        </div>
                    )}
                    {isAdmin && (
                        <div style={{ marginTop: '0.6rem' }}>
                            <Button
                                basic
                                color='red'
                                size='tiny'
                                icon='trash alternate outline'
                                content='Delete recording'
                                disabled={!t.id || deletingId === t.id}
                                loading={deletingId === t.id}
                                onClick={() => onDelete?.(t.id)}
                            />
                        </div>
                    )}
                </Segment>
            ))}
        </Segment>
    );
};

TranscriptPanel.propTypes = {
    transcripts: PropTypes.array,
    isAdmin: PropTypes.bool,
    deletingId: PropTypes.string,
    onDelete: PropTypes.func,
};

const IncidentEditModal = ({
    open,
    onClose,
    formId,
    sites,
    incidentFieldOptions,
    speechConfig,
    onSaved,
}) => {
    const { profile } = useAuth();
    const isAdmin = profile?.userLevel === 'administrator';

    const [editFormData, setEditFormData] = useState(null);
    const [editLoading, setEditLoading] = useState(false);
    const [editError, setEditError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [transcripts, setTranscripts] = useState(null);
    const [transcriptsError, setTranscriptsError] = useState(null);
    const [deletingTranscriptId, setDeletingTranscriptId] = useState(null);

    // Local voice recordings captured during THIS edit session.
    const [voiceTranscript, setVoiceTranscript] = useState('');
    const [recordings, setRecordings] = useState([]); // [{ blob, text, durationMs, startedAt }]
    const [voicePersistError, setVoicePersistError] = useState(null);
    const [errors, setErrors] = useState(EMPTY_ERRORS);
    const [showErrors, setShowErrors] = useState(false);

    useEffect(() => {
        if (!open || !formId) {
            setEditFormData(null);
            setEditError(null);
            setTranscripts(null);
            setTranscriptsError(null);
            setDeletingTranscriptId(null);
            setVoiceTranscript('');
            setRecordings([]);
            setVoicePersistError(null);
            setShowErrors(false);
            setErrors(EMPTY_ERRORS);
            return;
        }
        let cancelled = false;
        (async () => {
            setEditLoading(true);
            setEditError(null);
            setEditFormData(null);
            setTranscripts(null);
            setTranscriptsError(null);
            setDeletingTranscriptId(null);
            setVoiceTranscript('');
            setRecordings([]);
            setVoicePersistError(null);
            setShowErrors(false);
            setErrors(EMPTY_ERRORS);
            try {
                // Fetch incident first - if THAT fails, we abort.
                const data = await fetchIncidentFull(formId);
                if (cancelled) return;
                setEditFormData(data);

                // Transcripts are best-effort - don't fail the modal open, but
                // distinguish "really empty" from "fetch failed" so the panel
                // shows an error message instead of lying with "no transcripts".
                try {
                    const transcriptData = await fetchIncidentTranscripts(formId);
                    if (!cancelled) setTranscripts(transcriptData?.transcripts || []);
                } catch (transcriptErr) {
                    if (!cancelled) {
                        setTranscriptsError(transcriptErr.message || 'Failed to load transcripts');
                        setTranscripts([]);
                    }
                }
            } catch (e) {
                if (!cancelled) setEditError(e.message);
            } finally {
                if (!cancelled) setEditLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [open, formId]);

    const reloadTranscripts = useCallback(async () => {
        if (!formId) return;
        setTranscriptsError(null);
        try {
            const transcriptData = await fetchIncidentTranscripts(formId);
            setTranscripts(transcriptData?.transcripts || []);
        } catch (e) {
            setTranscriptsError(e.message || 'Failed to load transcripts');
        }
    }, [formId]);

    const handleSaveEdit = async (status) => {
        if (!editFormData || !formId) return;

        // "Save as Completed" enforces required fields; "Save as Draft" bypasses.
        if (status === 'completed') {
            const result = validateIncidentForm(editFormData);
            if (result.hasErrors) {
                setErrors(result);
                setShowErrors(true);
                scrollToFirstError();
                return;
            }
        }
        setShowErrors(false);
        setErrors(EMPTY_ERRORS);

        setSaving(true);
        setEditError(null);
        setVoicePersistError(null);
        try {
            await updateIncident(formId, editFormData, status);

            // Persist any new voice segments recorded during this edit session.
            // onSegmentSaved drops each successfully-saved segment from local
            // state so a retry after partial failure doesn't re-create them.
            const warnings = await persistTranscripts({
                incidentId: formId,
                recordings,
                liveTranscript: voiceTranscript,
                extractionMeta: null,
                onSegmentSaved: (savedSeg) => {
                    setRecordings((prev) => prev.filter((r) => r !== savedSeg));
                },
            });
            if (warnings.length > 0) {
                // Keep modal open so user can see what failed (incident save succeeded).
                setVoicePersistError(warnings.join(' '));
                await reloadTranscripts();
                return;
            }

            // Clear local state now that everything saved.
            setVoiceTranscript('');
            setRecordings([]);

            onClose();
            onSaved?.();
        } catch (e) {
            setEditError(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteTranscript = async (transcriptId) => {
        if (!isAdmin || !formId || !transcriptId) return;
        setDeletingTranscriptId(transcriptId);
        setTranscriptsError(null);
        try {
            await deleteTranscript(formId, transcriptId);
            await reloadTranscripts();
        } catch (e) {
            setTranscriptsError(e.message || 'Failed to delete transcript');
        } finally {
            setDeletingTranscriptId(null);
        }
    };

    const handleClose = () => {
        setEditFormData(null);
        setEditError(null);
        setTranscripts(null);
        setTranscriptsError(null);
        setDeletingTranscriptId(null);
        setVoiceTranscript('');
        setRecordings([]);
        setVoicePersistError(null);
        onClose();
    };

    return (
        <Modal
            open={open}
            onClose={handleClose}
            size='large'
            closeIcon
        >
            <Modal.Header>
                <Icon name='edit' />
                Edit Incident Report
            </Modal.Header>
            <Modal.Content scrolling>
                {editLoading && (
                    <Segment basic>
                        <Loader active inline='centered' content='Loading incident...' />
                    </Segment>
                )}
                {editError && (
                    <Message error>
                        <Icon name='warning circle' />
                        {editError}
                    </Message>
                )}
                {editFormData && !editLoading && (
                    <>
                        {speechConfig && (
                            <>
                                <Header as='h4' dividing>
                                    <Icon name='microphone' />
                                    Add voice recording
                                </Header>
                                {voicePersistError && (
                                    <Message warning size='small' onDismiss={() => setVoicePersistError(null)}>
                                        <Icon name='warning sign' />
                                        {voicePersistError}
                                    </Message>
                                )}
                                <VoiceInput
                                    speechConfig={speechConfig}
                                    transcript={voiceTranscript}
                                    onTranscriptChange={setVoiceTranscript}
                                    formType='incident'
                                    site={editFormData?.incident?.site || ''}
                                    extractionPrefix={(transcripts || [])
                                        .map((t) => (t.text || '').trim())
                                        .filter(Boolean)
                                        .join('\n\n')}
                                    onExtracted={(result) => {
                                        // Replace the form with the new extraction (mirrors
                                        // the create-flow behaviour) but preserve the user's
                                        // quickNote and the recorded createdDate. The
                                        // extraction is based on the combined transcript of
                                        // the already-saved recordings PLUS the new ones
                                        // captured in this edit session.
                                        setEditFormData((prev) => ({
                                            ...result,
                                            incident: {
                                                ...result.incident,
                                                quickNote: prev?.incident?.quickNote
                                                    || result.incident?.quickNote || '',
                                                createdDate: prev?.incident?.createdDate
                                                    ?? result.incident?.createdDate ?? null,
                                            },
                                        }));
                                    }}
                                    onRecordingsChange={setRecordings}
                                    submitted={false}
                                    submittedStatus={null}
                                />
                                <Divider />
                            </>
                        )}
                        {transcripts !== null && (
                            <>
                                <Header as='h4' dividing>
                                    <Icon name='microphone' />
                                    Voice Transcripts
                                </Header>
                                {transcriptsError && (
                                    <Message warning size='small'>
                                        <Icon name='warning sign' />
                                        Could not load transcripts: {transcriptsError}
                                    </Message>
                                )}
                                <TranscriptPanel
                                    transcripts={transcripts}
                                    isAdmin={isAdmin}
                                    deletingId={deletingTranscriptId}
                                    onDelete={handleDeleteTranscript}
                                />
                                <Divider />
                            </>
                        )}
                        <IncidentForm
                            data={editFormData}
                            onChange={setEditFormData}
                            fieldOptions={incidentFieldOptions}
                            sites={sites}
                            errors={errors}
                            showErrors={showErrors}
                        />
                    </>
                )}
            </Modal.Content>
            <Modal.Actions>
                <Button
                    color='green'
                    onClick={() => handleSaveEdit('completed')}
                    disabled={saving || editLoading || !editFormData}
                    loading={saving}
                    icon='check'
                    labelPosition='left'
                    content='Save as Completed'
                />
                <Button
                    color='yellow'
                    onClick={() => handleSaveEdit('draft')}
                    disabled={saving || editLoading || !editFormData}
                    loading={saving}
                    icon='save outline'
                    labelPosition='left'
                    content='Save as Draft'
                />
                <Button
                    onClick={handleClose}
                    disabled={saving}
                    content='Cancel'
                />
            </Modal.Actions>
        </Modal>
    );
};

IncidentEditModal.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    formId: PropTypes.string,
    sites: PropTypes.array.isRequired,
    incidentFieldOptions: PropTypes.object.isRequired,
    speechConfig: PropTypes.object,
    onSaved: PropTypes.func,
};

export default IncidentEditModal;
