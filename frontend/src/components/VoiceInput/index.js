import React, { useState, useRef, useCallback } from 'react';
import {
    Container,
    Grid,
    Segment,
    Button,
    Icon,
    Form,
    Header,
    Message,
    Loader,
} from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { extractForm } from '../../services/api';

const VoiceInput = ({
    speechConfig,
    transcript,
    onTranscriptChange,
    formType,
    site,
    onExtracted,
    submitted,
}) => {
    const [isRecording, setIsRecording] = useState(false);
    const [extracting, setExtracting] = useState(false);
    const [error, setError] = useState(null);
    const recognitionRef = useRef(null);
    const finalTranscriptRef = useRef('');

    const startRecording = useCallback(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setError('Speech recognition is not supported in this browser. Use Chrome or Edge.');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = speechConfig.continuous;
        recognition.interimResults = speechConfig.interim_results;
        recognition.lang = speechConfig.language;

        finalTranscriptRef.current = '';

        recognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const text = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscriptRef.current += text + ' ';
                } else {
                    interim = text;
                }
            }
            onTranscriptChange(finalTranscriptRef.current + interim);
        };

        recognition.onerror = (event) => {
            if (event.error !== 'no-speech') {
                setError('Microphone error: ' + event.error);
            }
            stopRecording();
        };

        recognition.onend = () => {
            if (recognitionRef.current) {
                try { recognition.start(); } catch (e) { /* already started */ }
            }
        };

        recognition.start();
        recognitionRef.current = recognition;
        setIsRecording(true);
        setError(null);
    }, [speechConfig, onTranscriptChange]);

    const stopRecording = useCallback(() => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
            recognitionRef.current = null;
        }
        setIsRecording(false);
    }, []);

    const toggleRecording = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    const handleExtract = async () => {
        if (!transcript.trim()) {
            setError('No transcript to extract from. Please speak first.');
            return;
        }

        setExtracting(true);
        setError(null);

        try {
            const result = await extractForm(transcript, formType, site);
            onExtracted(result);
        } catch (e) {
            setError('Extraction failed: ' + e.message);
        } finally {
            setExtracting(false);
        }
    };

    if (submitted) {
        return (
            <Container style={{ paddingTop: '1rem' }}>
                <Message success icon>
                    <Icon name='check circle' />
                    <Message.Content>
                        <Message.Header>Form submitted successfully</Message.Header>
                        The data has been saved as a draft. Open SKSSIR to review and finalize.
                    </Message.Content>
                </Message>
            </Container>
        );
    }

    return (
        <Container style={{ paddingTop: '1rem' }}>
            <Grid container>
                <Grid.Row centered>
                    <Segment basic textAlign='center'>
                        <Button
                            circular
                            icon
                            size='massive'
                            className={`mic-button ${isRecording ? 'recording' : ''}`}
                            onClick={toggleRecording}
                            color={isRecording ? 'red' : 'blue'}
                        >
                            <Icon name='microphone' />
                        </Button>
                        <Header as='h4' color='grey' style={{ marginTop: '1rem' }}>
                            {isRecording ? 'Listening... tap to stop' : 'Tap to start speaking'}
                        </Header>
                    </Segment>
                </Grid.Row>

                {error && (
                    <Grid.Row>
                        <Grid.Column width={16}>
                            <Message error content={error} onDismiss={() => setError(null)} />
                        </Grid.Column>
                    </Grid.Row>
                )}

                {transcript && (
                    <Grid.Row>
                        <Grid.Column width={16}>
                            <Segment color='blue'>
                                <Header as='h3'>Transcript</Header>
                                <Form>
                                    <Form.TextArea
                                        rows={4}
                                        value={transcript}
                                        onChange={(e, { value }) => onTranscriptChange(value)}
                                        placeholder='Your speech will appear here...'
                                    />
                                </Form>
                                <Button
                                    color='green'
                                    size='large'
                                    style={{ marginTop: '1rem' }}
                                    onClick={handleExtract}
                                    disabled={extracting || !transcript.trim()}
                                    loading={extracting}
                                    icon='magic'
                                    labelPosition='left'
                                    content='Extract Form Data'
                                />
                                {extracting && (
                                    <Loader active inline size='small' style={{ marginLeft: '1rem' }} />
                                )}
                            </Segment>
                        </Grid.Column>
                    </Grid.Row>
                )}
            </Grid>
        </Container>
    );
};

VoiceInput.propTypes = {
    speechConfig: PropTypes.object.isRequired,
    transcript: PropTypes.string.isRequired,
    onTranscriptChange: PropTypes.func.isRequired,
    formType: PropTypes.string.isRequired,
    site: PropTypes.string.isRequired,
    onExtracted: PropTypes.func.isRequired,
    submitted: PropTypes.bool.isRequired,
};

export default VoiceInput;
