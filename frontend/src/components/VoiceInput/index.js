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
    Label,
} from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { extractForm, transcribeAudio } from '../../services/api';

const AUDIO_ENABLED = process.env.REACT_APP_ENABLE_AUDIO === '1';
const WHISPER_ENABLED = process.env.REACT_APP_ENABLE_WHISPER !== '0';

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

const formatTime = (ms) => {
    if (!ms) return '';
    try {
        return new Date(ms).toLocaleTimeString([], {
            hour: '2-digit', minute: '2-digit', second: '2-digit',
        });
    } catch (e) { return ''; }
};

const formatDuration = (ms) => {
    if (!ms || ms < 0) return '';
    const s = Math.round(ms / 1000);
    const mm = Math.floor(s / 60);
    const ss = (s % 60).toString().padStart(2, '0');
    return `${mm}:${ss}`;
};

let _segmentCounter = 0;

const VoiceInput = ({
    speechConfig,
    transcript,
    onTranscriptChange,
    formType,
    site,
    onExtracted,
    onRecordingsChange,
    submitted,
    submittedStatus,
    extractionPrefix,
}) => {
    const [isRecording, setIsRecording] = useState(false);
    const [extracting, setExtracting] = useState(false);
    const [error, setError] = useState(null);
    const [warning, setWarning] = useState(null);
    // List of completed recording segments. Each segment is one upcoming
    // transcript record on submit. The data model already supports many
    // transcripts per incident.
    const [segments, setSegments] = useState([]);
    const recognitionRef = useRef(null);
    // Speech-recognition state for the CURRENT segment only. Each new
    // recording resets these but the parent `transcript` keeps growing.
    const finalTranscriptRef = useRef('');
    const segmentBaseRef = useRef('');     // transcript value at this segment's start
    const segmentStartIdxRef = useRef(0);  // index in master transcript where this segment begins
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const mediaStreamRef = useRef(null);
    const recordingStartMsRef = useRef(null);
    const liveTextRef = useRef('');
    // Track latest transcript prop in a ref so callbacks see the current
    // value without needing to be re-created on every keystroke.
    const transcriptRef = useRef(transcript);
    useEffect(() => { transcriptRef.current = transcript; }, [transcript]);

    // Bubble segment changes up to the parent (App.js) so the submit flow
    // sees the full list when persisting.
    useEffect(() => {
        if (onRecordingsChange) {
            onRecordingsChange(segments.map((s) => ({
                blob: s.blob,
                text: s.text,
                durationMs: s.durationMs,
                startedAt: s.startedAt,
            })));
        }
    }, [segments, onRecordingsChange]);

    // Track latest segments in a ref so the unmount cleanup sees the final
    // list without re-running on every change. Avoids the eslint
    // exhaustive-deps warning while still cleaning up reliably on unmount.
    const segmentsRef = useRef(segments);
    useEffect(() => { segmentsRef.current = segments; }, [segments]);
    useEffect(() => {
        return () => {
            segmentsRef.current.forEach((s) => {
                if (s.previewUrl) URL.revokeObjectURL(s.previewUrl);
            });
        };
    }, []);

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

    const startAudioCapture = useCallback(async (segmentText) => {
        if (!AUDIO_ENABLED) {
            return;
        }
        if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
            setWarning('Audio recording is not supported in this browser. Speech-to-text may still work.');
            return;
        }
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
                const startedAt = recordingStartMsRef.current || Date.now();
                const durationMs = startedAt ? Date.now() - startedAt : 0;
                audioChunksRef.current = [];
                if (blob.size === 0) return;
                const segmentBaseStart = segmentStartIdxRef.current;
                const fullText = liveTextRef.current;
                const webSpeechText = fullText.slice(segmentBaseStart).trim();
                const segment = {
                    id: `seg-${++_segmentCounter}`,
                    blob,
                    text: webSpeechText,
                    durationMs,
                    startedAt,
                    previewUrl: URL.createObjectURL(blob),
                    polishing: WHISPER_ENABLED,
                };
                setSegments((prev) => [...prev, segment]);

                // Background quality pass: send the blob to Whisper and
                // replace the segment text + the slice of the master
                // transcript that came from this segment. Web Speech text
                // is kept as a fallback if the call fails.
                if (WHISPER_ENABLED) {
                    transcribeAudio(blob).then((polishedText) => {
                        if (!polishedText) {
                            markSegmentDonePolishing(segment.id);
                            return;
                        }
                        replaceSegmentText(segment.id, segmentBaseStart, webSpeechText, polishedText);
                    }).catch((err) => {
                        // 503 = OPENAI_API_KEY unset, just hide the indicator.
                        // Anything else logs but keeps the Web Speech text.
                        // eslint-disable-next-line no-console
                        console.warn('Whisper transcription failed; keeping live text:', err.message);
                        markSegmentDonePolishing(segment.id);
                    });
                }
            };
            recorder.start();
            mediaRecorderRef.current = recorder;
        } catch (e) {
            const reason = e?.name === 'NotAllowedError'
                ? 'Microphone permission was denied'
                : (e?.message || 'Audio recording failed to start');
            setWarning(
                `${reason}. Voice transcript will still try to record but no audio file will be saved. `
                + `Click the camera icon in your browser address bar to grant microphone access, then reload.`
            );
        }
    }, []);

    const startRecording = useCallback(async () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setError('Speech recognition is not supported in this browser. Use Chrome or Edge.');
            return;
        }

        // Master transcript continues to accumulate across recordings; insert
        // a timestamp marker so the boundary is clear in the textarea. Read
        // current transcript via ref so the callback dep list doesn't need to
        // rebuild on every keystroke.
        const now = new Date();
        const ts = now.toLocaleTimeString([], {
            hour: '2-digit', minute: '2-digit', second: '2-digit',
        });
        const current = transcriptRef.current || '';
        const prefix = current ? `${current.replace(/\s+$/, '')}\n\n[${ts}] ` : `[${ts}] `;
        segmentBaseRef.current = prefix;
        segmentStartIdxRef.current = prefix.length;
        finalTranscriptRef.current = '';
        liveTextRef.current = prefix;
        onTranscriptChange(prefix);

        await startAudioCapture();

        const recognition = new SpeechRecognition();
        recognition.continuous = speechConfig.continuous;
        recognition.interimResults = speechConfig.interim_results;
        recognition.lang = speechConfig.language;

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
            const live = segmentBaseRef.current + finalTranscriptRef.current + interim;
            liveTextRef.current = live;
            onTranscriptChange(live);
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

    const markSegmentDonePolishing = (segmentId) => {
        setSegments((prev) => prev.map((s) =>
            s.id === segmentId ? { ...s, polishing: false } : s,
        ));
    };

    /**
     * Whisper returned a higher-accuracy transcript for a segment. Update:
     *   1. The segment record (so its `text` reflects the polished version)
     *   2. The master `transcript` prop - splice out the slice that came
     *      from this segment and replace it with the polished text. The
     *      timestamp marker at the segment boundary stays intact.
     */
    const replaceSegmentText = (segmentId, baseStart, oldText, newText) => {
        setSegments((prev) => prev.map((s) =>
            s.id === segmentId ? { ...s, text: newText, polishing: false } : s,
        ));

        const current = transcriptRef.current || '';
        // Find the segment's slice. We expect it to start at baseStart and
        // run until the next segment boundary (next "\n\n[" marker) or EOF.
        const tail = current.slice(baseStart);
        const nextBoundary = tail.search(/\n\n\[\d/);
        const sliceEnd = nextBoundary === -1 ? current.length : baseStart + nextBoundary;
        const before = current.slice(0, baseStart);
        const after = current.slice(sliceEnd);
        // Preserve any extra whitespace/newlines after the polished text
        // before the next segment boundary.
        const updated = `${before}${newText.trim()}${after}`;
        liveTextRef.current = updated;
        onTranscriptChange(updated);
    };

    const discardSegment = (segmentId) => {
        setSegments((prev) => {
            const next = prev.filter((s) => {
                if (s.id === segmentId) {
                    if (s.previewUrl) URL.revokeObjectURL(s.previewUrl);
                    return false;
                }
                return true;
            });
            return next;
        });
    };

    const handleExtract = async () => {
        const newText = (transcript || '').trim();
        const prefix = (extractionPrefix || '').trim();
        // When called from the edit-draft modal, prefix contains the
        // already-saved transcripts so the AI sees the full combined context.
        const allText = prefix && newText
            ? `${prefix}\n\n${newText}`
            : (newText || prefix);
        if (!allText) {
            setError('No transcript to extract from. Please speak first.');
            return;
        }

        setExtracting(true);
        setError(null);

        const started = Date.now();
        try {
            const result = await extractForm(allText, formType, site);
            onExtracted(result, { latencyMs: Date.now() - started });
        } catch (e) {
            setError('Extraction failed: ' + e.message);
        } finally {
            setExtracting(false);
        }
    };

    if (submitted) {
        const isDraft = submittedStatus === 'draft';
        return (
            <Container style={{ paddingTop: '1rem' }}>
                <Message success icon>
                    <Icon name={isDraft ? 'save outline' : 'check circle'} />
                    <Message.Content>
                        <Message.Header>
                            {isDraft ? 'Saved as draft' : 'Incident submitted'}
                        </Message.Header>
                        {isDraft ? (
                            <>
                                Your incident is saved as a draft and won't appear in
                                statistics until you mark it complete. Open it from
                                <strong> My Incidents</strong> to keep editing.
                            </>
                        ) : (
                            <>
                                Your incident has been submitted and will appear in
                                statistics. You can still view or edit it from
                                <strong> My Incidents</strong>.
                            </>
                        )}
                    </Message.Content>
                </Message>
            </Container>
        );
    }

    const hasAnyContent = transcript.trim() || segments.length > 0;
    const isTranscribing = segments.some((s) => s.polishing);

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
                            {isRecording
                                ? 'Listening... tap to stop'
                                : segments.length > 0
                                    ? 'Tap to add another recording'
                                    : 'Tap to start speaking'}
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

                {/* Combined transcript - accumulates across recordings */}
                {transcript && (
                    <Grid.Row>
                        <Grid.Column width={16}>
                            <Segment color='blue'>
                                <Header as='h3'>
                                    <Icon name='align left' color='blue' />
                                    Transcript
                                </Header>
                                <Form>
                                    <Form.TextArea
                                        rows={6}
                                        value={transcript}
                                        onChange={(e, { value }) => onTranscriptChange(value)}
                                        placeholder='Your speech will appear here...'
                                    />
                                </Form>
                                <p style={{ fontSize: '0.8rem', color: '#888', marginTop: '0.4rem' }}>
                                    {isRecording
                                        ? 'Listening - speak now. Tap stop and tap mic again to add another recording.'
                                        : 'You can edit the text above. Tap the mic to add another recording.'}
                                </p>
                            </Segment>
                        </Grid.Column>
                    </Grid.Row>
                )}

                {/* Saved audio recordings list */}
                {segments.length > 0 && (
                    <Grid.Row>
                        <Grid.Column width={16}>
                            <Segment color='teal'>
                                <Header as='h4'>
                                    <Icon name='headphones' color='teal' />
                                    {`Audio recordings (${segments.length})`}
                                </Header>
                                <p style={{ fontSize: '0.8rem', color: '#888' }}>
                                    Each recording is saved as a separate audio file linked to this incident.
                                    Discard a recording to remove its audio (the transcript text stays).
                                </p>
                                {segments.map((s, idx) => (
                                    <Segment key={s.id} secondary>
                                        <Header as='h5' style={{ marginBottom: '0.4rem' }}>
                                            <Icon name='play circle' color='blue' />
                                            {`Recording ${idx + 1}`}
                                            <Label size='tiny' style={{ marginLeft: '0.6rem' }}>
                                                {formatTime(s.startedAt)}
                                            </Label>
                                            {s.durationMs > 0 && (
                                                <Label size='tiny'>{formatDuration(s.durationMs)}</Label>
                                            )}
                                            {s.polishing && (
                                                <Label size='tiny' color='yellow'>
                                                    <Icon name='magic' />
                                                    Transcribing with Whisper&hellip;
                                                </Label>
                                            )}
                                        </Header>
                                        {s.previewUrl && (
                                            <audio controls src={s.previewUrl} style={{ width: '100%', marginBottom: '0.4rem' }} />
                                        )}
                                        <Button
                                            basic
                                            color='red'
                                            size='tiny'
                                            icon='trash alternate outline'
                                            content='Discard recording'
                                            onClick={() => discardSegment(s.id)}
                                        />
                                    </Segment>
                                ))}
                            </Segment>
                        </Grid.Column>
                    </Grid.Row>
                )}

                {hasAnyContent && (
                    <Grid.Row>
                        <Grid.Column width={16}>
                            <Button
                                color='green'
                                size='large'
                                onClick={handleExtract}
                                disabled={extracting || isTranscribing || !transcript.trim()}
                                loading={extracting}
                                icon='magic'
                                labelPosition='left'
                                content='Extract Form Data'
                            />
                            {extracting && (
                                <Loader active inline size='small' style={{ marginLeft: '1rem' }} />
                            )}
                            {isTranscribing && !extracting && (
                                <span style={{ marginLeft: '1rem', color: '#888', fontSize: '0.9rem' }}>
                                    <Icon name='magic' /> Whisper is finalising the transcript&hellip; extraction will be available once it&rsquo;s ready.
                                </span>
                            )}
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
    onRecordingsChange: PropTypes.func,
    submitted: PropTypes.bool.isRequired,
    submittedStatus: PropTypes.oneOf(['completed', 'draft', null]),
    extractionPrefix: PropTypes.string,
};

export default VoiceInput;
