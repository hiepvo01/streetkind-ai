import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Button, Divider, Header, Icon, Label, Loader, Message, Modal, Segment } from 'semantic-ui-react';

import { fetchIncidentFull, fetchIncidentTranscripts, updateIncident } from '../../services/api';
import IncidentForm from '../forms/IncidentForm';

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

const TranscriptPanel = ({ transcripts }) => {
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
                    ) : null}
                    <p style={{ whiteSpace: 'pre-wrap', marginTop: '0.3rem' }}>{t.text}</p>
                    {t.extractionMeta && (t.extractionMeta.model || t.extractionMeta.latencyMs) && (
                        <div style={{ fontSize: '0.75rem', color: '#888' }}>
                            {t.extractionMeta.model && <span>Model: {t.extractionMeta.model}  </span>}
                            {t.extractionMeta.latencyMs > 0 && <span>Latency: {t.extractionMeta.latencyMs}ms</span>}
                        </div>
                    )}
                </Segment>
            ))}
        </Segment>
    );
};

TranscriptPanel.propTypes = {
    transcripts: PropTypes.array,
};

const IncidentEditModal = ({
    open,
    onClose,
    formId,
    sites,
    incidentFieldOptions,
    onSaved,
}) => {
    const [editFormData, setEditFormData] = useState(null);
    const [editLoading, setEditLoading] = useState(false);
    const [editError, setEditError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [transcripts, setTranscripts] = useState(null);

    useEffect(() => {
        if (!open || !formId) {
            setEditFormData(null);
            setEditError(null);
            setTranscripts(null);
            return;
        }
        let cancelled = false;
        (async () => {
            setEditLoading(true);
            setEditError(null);
            setEditFormData(null);
            setTranscripts(null);
            try {
                const [data, transcriptData] = await Promise.all([
                    fetchIncidentFull(formId),
                    fetchIncidentTranscripts(formId).catch(() => ({ transcripts: [] })),
                ]);
                if (!cancelled) {
                    setEditFormData(data);
                    setTranscripts(transcriptData?.transcripts || []);
                }
            } catch (e) {
                if (!cancelled) setEditError(e.message);
            } finally {
                if (!cancelled) setEditLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [open, formId]);

    const handleSaveEdit = async (status) => {
        if (!editFormData || !formId) return;
        setSaving(true);
        setEditError(null);
        try {
            await updateIncident(formId, editFormData, status);
            onClose();
            onSaved?.();
        } catch (e) {
            setEditError(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleClose = () => {
        setEditFormData(null);
        setEditError(null);
        setTranscripts(null);
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
                        {transcripts !== null && (
                            <>
                                <Header as='h4' dividing>
                                    <Icon name='microphone' />
                                    Voice Transcripts
                                </Header>
                                <TranscriptPanel transcripts={transcripts} />
                                <Divider />
                            </>
                        )}
                        <IncidentForm
                            data={editFormData}
                            onChange={setEditFormData}
                            fieldOptions={incidentFieldOptions}
                            sites={sites}
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
    onSaved: PropTypes.func,
};

export default IncidentEditModal;
