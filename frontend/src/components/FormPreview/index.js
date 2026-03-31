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

import { submitForm } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import IncidentForm from '../forms/IncidentForm';
import SafeBaseForm from '../forms/SafeBaseForm';

const FormPreview = ({ formType, data, onDataChange, onSubmitted, onReset, fieldOptions, sites }) => {
    const { user } = useAuth();
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [accordionActive, setAccordionActive] = useState(false);

    const handleSubmit = async () => {
        setSubmitting(true);
        setError(null);

        try {
            await submitForm(formType, data, user.uid);
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
                                    Extracted Form Data
                                    <Header.Subheader>
                                        Review and edit before submitting
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
                                    fieldOptions={fieldOptions.safebase || []}
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

                            <div style={{ marginTop: '1rem' }}>
                                <Button
                                    color='green'
                                    size='large'
                                    onClick={handleSubmit}
                                    disabled={submitting}
                                    loading={submitting}
                                    icon='check'
                                    labelPosition='left'
                                    content='Confirm & Submit'
                                />
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
};

export default FormPreview;
