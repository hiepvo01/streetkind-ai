import React, { useState } from 'react';
import {
    Accordion,
    Button,
    Container,
    Grid,
    Header,
    Icon,
    Message,
    Segment,
} from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { submitForm, createTranscript, uploadTranscriptAudio } from '../../services/api';
import IncidentForm from '../forms/IncidentForm';
import SafeBaseForm from '../forms/SafeBaseForm';

const AUDIO_ENABLED = process.env.REACT_APP_ENABLE_AUDIO === '1';

const FormPreview = ({
    formType,
    data,
    onDataChange,
    onSubmitted,
    onReset,
    fieldOptions,
    sites,
    transcript,
    recordings,
    extractionMeta,
}) => {
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [accordionActive, setAccordionActive] = useState(false);

    /**
     * Save transcripts (and audio if enabled) after the incident was submitted.
     *
     * One transcript record is created per recorded segment, plus a final
     * record if there is live transcript text not yet captured into a segment
     * (the user typed/spoke it but didn't tap stop). Each segment carries its
     * own audio blob.
     *
     * Returns a list of non-fatal warning strings: the incident itself is
     * already saved, so transcript/audio failures must not look like submit
     * failures but also must not be silent (the transcript is the audit trail).
     */
    const persistTranscript = async (incidentId) => {
        const warnings = [];
        const items = [];

        // 1. Each saved segment becomes one transcript with its own audio.
        (recordings || []).forEach((seg) => {
            if ((seg.text && seg.text.trim()) || seg.blob) {
                items.push({
                    text: seg.text || '',
                    durationMs: seg.durationMs || 0,
                    blob: seg.blob || null,
                });
            }
        });

        // 2. If the user has live text in the textarea that wasn't saved into
        //    a segment yet (e.g. they typed manually instead of using mic),
        //    persist it as a text-only transcript.
        const liveText = (transcript || '').trim();
        const liveAlreadyCovered = items.some((i) => (i.text || '').trim() === liveText);
        if (liveText && !liveAlreadyCovered) {
            items.push({ text: liveText, durationMs: 0, blob: null });
        }

        if (items.length === 0) return warnings;

        for (const item of items) {
            let transcriptId;
            try {
                const res = await createTranscript(
                    incidentId,
                    item.text,
                    item.durationMs,
                    extractionMeta || null,
                );
                transcriptId = res.transcriptId;
            } catch (transcriptErr) {
                warnings.push(
                    `Voice transcript was not saved: ${transcriptErr.message}. `
                    + `The incident report itself was saved successfully.`,
                );
                continue;
            }

            if (AUDIO_ENABLED && item.blob && transcriptId) {
                try {
                    await uploadTranscriptAudio(incidentId, transcriptId, item.blob);
                } catch (audioErr) {
                    warnings.push(
                        `Audio recording upload failed: ${audioErr.message}. `
                        + `The text transcript was saved.`,
                    );
                }
            }
        }

        return warnings;
    };

    const handleSubmit = async (status = 'completed') => {
        setSubmitting(true);
        setError(null);

        try {
            const result = await submitForm(formType, data, status);
            if (formType === 'incident' && result?.key) {
                const warnings = await persistTranscript(result.key);
                if (warnings.length > 0) {
                    setError(warnings.join(' '));
                    // Don't call onSubmitted - keep the form visible so the user
                    // can see the warning and decide whether to retry.
                    return;
                }
            }
            // createdDate is assigned server-side on first save; set a local value so the UI
            // can display immediately without requiring a reload/edit round-trip.
            if (formType === 'incident') {
                const existing = data?.incident?.createdDate;
                if (!existing) {
                    onDataChange({
                        ...data,
                        incident: {
                            ...data.incident,
                            createdDate: Date.now(),
                        },
                    });
                }
            }
            onSubmitted();
        } catch (e) {
            setError('Submit failed: ' + e.message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Container style={{ paddingTop: '1rem', paddingBottom: '2rem' }}>
            <Grid container>
                <Grid.Row>
                    <Grid.Column width={16}>
                        <Segment color='blue' raised>
                            <Header as='h3'>
                                <Icon name='file alternate outline' />
                                <Header.Content>
                                    Form data
                                    <Header.Subheader>
                                        Fill in manually or use voice, then review before submitting
                                    </Header.Subheader>
                                </Header.Content>
                            </Header>

                            {error && (
                                <Message error content={error} onDismiss={() => setError(null)} />
                            )}

                            {formType === 'incident' && (
                                <IncidentForm
                                    data={data}
                                    onChange={onDataChange}
                                    fieldOptions={{ ...(fieldOptions.incident || {}), ...(fieldOptions.client || {}) }}
                                    sites={sites}
                                />
                            )}

                            {formType === 'safebase' && (
                                <SafeBaseForm
                                    data={data}
                                    onChange={onDataChange}
                                    fieldOptions={fieldOptions.safebase || {}}
                                />
                            )}

                            <Accordion style={{ marginTop: '1rem' }}>
                                <Accordion.Title
                                    active={accordionActive}
                                    onClick={() => setAccordionActive(!accordionActive)}
                                >
                                    <Icon name='dropdown' />
                                    Raw JSON (debug)
                                </Accordion.Title>
                                <Accordion.Content active={accordionActive}>
                                    <pre style={{ fontSize: '0.8rem', maxHeight: '300px', overflow: 'auto' }}>
                                        {JSON.stringify(data, null, 2)}
                                    </pre>
                                </Accordion.Content>
                            </Accordion>

                            <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                <Button
                                    color='green'
                                    size='large'
                                    onClick={() => handleSubmit('completed')}
                                    disabled={submitting}
                                    loading={submitting}
                                    icon='check'
                                    labelPosition='left'
                                    content='Confirm & Submit'
                                />
                                {formType === 'incident' && (
                                    <Button
                                        color='yellow'
                                        size='large'
                                        onClick={() => handleSubmit('draft')}
                                        disabled={submitting}
                                        loading={submitting}
                                        icon='save outline'
                                        labelPosition='left'
                                        content='Save as Draft'
                                    />
                                )}
                                <Button
                                    color='red'
                                    size='large'
                                    onClick={onReset}
                                    disabled={submitting}
                                    icon='undo alternate'
                                    labelPosition='left'
                                    content='Start Over'
                                />
                            </div>
                        </Segment>
                    </Grid.Column>
                </Grid.Row>
            </Grid>
        </Container>
    );
};

FormPreview.propTypes = {
    formType: PropTypes.string.isRequired,
    data: PropTypes.object.isRequired,
    onDataChange: PropTypes.func.isRequired,
    onSubmitted: PropTypes.func.isRequired,
    onReset: PropTypes.func.isRequired,
    fieldOptions: PropTypes.object.isRequired,
    sites: PropTypes.array.isRequired,
    transcript: PropTypes.string,
    recordings: PropTypes.array,
    extractionMeta: PropTypes.object,
};

export default FormPreview;
