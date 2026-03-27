import React, { useState } from 'react';
import {
    Container,
    Grid,
    Segment,
    Button,
    Header,
    Message,
    Icon,
} from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { submitForm } from '../../services/api';

const FormPreview = ({ formType, data, onDataChange, onSubmitted, onReset }) => {
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [editableJson, setEditableJson] = useState(JSON.stringify(data, null, 2));

    const handleSubmit = async () => {
        // Parse the potentially edited JSON
        let parsedData;
        try {
            parsedData = JSON.parse(editableJson);
        } catch (e) {
            setError('The edited JSON is invalid. Please fix it or start over.');
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            // TODO: In production, user_uid comes from Firebase Auth session
            await submitForm(formType, parsedData, 'demo-user');
            onDataChange(parsedData);
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

                            <Segment className='form-preview-json'>
                                <pre
                                    contentEditable
                                    suppressContentEditableWarning
                                    onBlur={(e) => setEditableJson(e.target.innerText)}
                                    style={{ outline: 'none', minHeight: '200px' }}
                                >
                                    {JSON.stringify(data, null, 2)}
                                </pre>
                            </Segment>

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
};

export default FormPreview;
