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
    recording,
    extractionMeta,
}) => {
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [accordionActive, setAccordionActive] = useState(false);

    const persistTranscript = async (incidentId) => {
        if (!transcript || !transcript.trim()) return;
        try {
            const { transcriptId } = await createTranscript(
                incidentId,
                transcript,
                recording?.durationMs || 0,
                extractionMeta || null,
            );
            if (AUDIO_ENABLED && recording?.blob) {
                try {
                    await uploadTranscriptAudio(incidentId, transcriptId, recording.blob);
                } catch (audioErr) {
                    // Audio upload is best-effort - the text transcript is the
                    // primary audit artefact. Surface a non-blocking warning.
                    console.warn('Audio upload failed:', audioErr.message);
                }
            }
        } catch (transcriptErr) {
            console.warn('Transcript save failed:', transcriptErr.message);
        }
    };

    const handleSubmit = async (status = 'completed') => {
        setSubmitting(true);
        setError(null);

        try {
            const result = await submitForm(formType, data, status);
            if (formType === 'incident' && result?.key) {
                await persistTranscript(result.key);
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
    recording: PropTypes.object,
    extractionMeta: PropTypes.object,
};

export default FormPreview;
