import React, { useState, useRef, useCallback, useEffect } from 'react';
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

const AUDIO_ENABLED = process.env.REACT_APP_ENABLE_AUDIO === '1';

const PREFERRED_AUDIO_TYPES = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg',
];

const pickAudioMimeType = () => {
    if (typeof MediaRecorder === 'undefined') return null;
    for (const t of PREFERRED_AUDIO_TYPES) {
        if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return '';
};

const VoiceInput = ({
    speechConfig,
    transcript,
    onTranscriptChange,
    formType,
    site,
    onExtracted,
    onRecordingCaptured,
    submitted,
}) => {
    const [isRecording, setIsRecording] = useState(false);
    const [extracting, setExtracting] = useState(false);
    const [error, setError] = useState(null);
    const [warning, setWarning] = useState(null);
    const [previewUrl, setPreviewUrl] = useState(null);
    const recognitionRef = useRef(null);
    const finalTranscriptRef = useRef('');
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const mediaStreamRef = useRef(null);
    const recordingStartMsRef = useRef(null);

    // Revoke any object URL when this component unmounts or a new recording
    // replaces it - browsers leak memory otherwise.
    useEffect(() => {
        return () => {
            if (previewUrl) URL.revokeObjectURL(previewUrl);
        };
    }, [previewUrl]);

    const stopAudioCapture = useCallback(() => {
        const mr = mediaRecorderRef.current;
        if (mr && mr.state !== 'inactive') {
            try { mr.stop(); } catch (e) { /* already stopping */ }
        }
        mediaRecorderRef.current = null;
        const stream = mediaStreamRef.current;
        if (stream) {
            stream.getTracks().forEach((t) => t.stop());
            mediaStreamRef.current = null;
        }
    }, []);

    const stopRecording = useCallback(() => {
        if (recognitionRef.current) {
            const rec = recognitionRef.current;
            recognitionRef.current = null; // prevent auto-restart in onend
            try { rec.stop(); } catch (e) { /* already stopped */ }
        }
        stopAudioCapture();
        setIsRecording(false);
    }, [stopAudioCapture]);

    const startAudioCapture = useCallback(async () => {
        if (!AUDIO_ENABLED) {
            return; // audio storage disabled at build time (REACT_APP_ENABLE_AUDIO)
        }
        if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
            setWarning('Audio recording is not supported in this browser. Speech-to-text may still work.');
            return;
        }
        // Clear any prior preview so the player resets for the new recording.
        setPreviewUrl((prev) => {
            if (prev) URL.revokeObjectURL(prev);
            return null;
        });
        setWarning(null);
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaStreamRef.current = stream;
            const mimeType = pickAudioMimeType();
            const recorder = mimeType
                ? new MediaRecorder(stream, { mimeType })
                : new MediaRecorder(stream);
            audioChunksRef.current = [];
            recordingStartMsRef.current = Date.now();
            recorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
            };
            recorder.onstop = () => {
                const type = recorder.mimeType || 'audio/webm';
                const blob = new Blob(audioChunksRef.current, { type });
                const durationMs = recordingStartMsRef.current
                    ? Date.now() - recordingStartMsRef.current
                    : 0;
                audioChunksRef.current = [];
                if (blob.size > 0) {
                    // Local preview URL for immediate playback before submit.
                    setPreviewUrl((prev) => {
                        if (prev) URL.revokeObjectURL(prev);
                        return URL.createObjectURL(blob);
                    });
                    if (onRecordingCaptured) onRecordingCaptured({ blob, durationMs });
                }
            };
            recorder.start();
            mediaRecorderRef.current = recorder;
        } catch (e) {
            // Mic permission denied or hardware issue - surface a non-blocking
            // warning so the volunteer knows audio won't be saved. Speech-to-text
            // may still work (it asks for its own permission via the
            // SpeechRecognition API).
            const reason = e?.name === 'NotAllowedError'
                ? 'Microphone permission was denied'
                : (e?.message || 'Audio recording failed to start');
            setWarning(
                `${reason}. Voice transcript will still try to record but no audio file will be saved. `
                + `Click the camera icon in your browser address bar to grant microphone access, then reload.`
            );
        }
    }, [onRecordingCaptured]);

    const startRecording = useCallback(async () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setError('Speech recognition is not supported in this browser. Use Chrome or Edge.');
            return;
        }

        await startAudioCapture();

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
    }, [speechConfig, onTranscriptChange, startAudioCapture, stopRecording]);

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

        const started = Date.now();
        try {
            const result = await extractForm(transcript, formType, site);
            onExtracted(result, { latencyMs: Date.now() - started });
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

                {warning && (
                    <Grid.Row>
                        <Grid.Column width={16}>
                            <Message warning onDismiss={() => setWarning(null)}>
                                <Message.Header>
                                    <Icon name='warning sign' />
                                    Audio recording disabled
                                </Message.Header>
                                <p>{warning}</p>
                            </Message>
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
                                {previewUrl && (
                                    <div style={{ marginTop: '0.75rem' }}>
                                        <Header as='h5' style={{ marginBottom: '0.3rem' }}>
                                            <Icon name='play circle' color='blue' />
                                            Recording preview
                                        </Header>
                                        <audio
                                            controls
                                            src={previewUrl}
                                            style={{ width: '100%' }}
                                        />
                                    </div>
                                )}
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
    onRecordingCaptured: PropTypes.func,
    submitted: PropTypes.bool.isRequired,
};

export default VoiceInput;
