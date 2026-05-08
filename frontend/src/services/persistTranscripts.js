/**
 * Save voice recordings + transcript text against an incident, returning
 * non-fatal warnings so callers can decide how to surface failures.
 *
 * Used by FormPreview (initial submit) and IncidentEditModal (adding new
 * recordings during edit). Centralised so the prompt / schema contract is
 * implemented once.
 *
 * Idempotency: each successfully-saved segment is removed from the input
 * `recordings` array via the optional `onSegmentSaved` callback so a retry
 * after a partial failure doesn't re-create the segments that already
 * landed.
 */

import { createTranscript, uploadTranscriptAudio } from './api';

const AUDIO_ENABLED = process.env.REACT_APP_ENABLE_AUDIO === '1';


/**
 * @param {Object}   args
 * @param {string}   args.incidentId      Push ID of the parent incident.
 * @param {Array}    args.recordings      [{ blob, text, durationMs, startedAt? }, ...]
 * @param {string}   [args.liveTranscript]  Master transcript textarea content. Persisted as a final
 *                                        text-only transcript if not already covered by a segment.
 * @param {Object}   [args.extractionMeta]  AI extraction metadata to attach to the FIRST transcript
 *                                        (model, latency, tokens). Optional.
 * @param {Function} [args.onSegmentSaved]  Called as `(segment)` after each successful save so the
 *                                        caller can drop it from local state. Used to prevent
 *                                        duplicate creation on retry after partial failure.
 * @returns {Promise<string[]>}  Non-fatal warning strings. Empty array means success.
 */
export async function persistTranscripts({
    incidentId,
    recordings = [],
    liveTranscript = '',
    extractionMeta = null,
    onSegmentSaved = null,
}) {
    const warnings = [];
    const items = [];

    (recordings || []).forEach((seg) => {
        if ((seg.text && seg.text.trim()) || seg.blob) {
            items.push({
                ref: seg, // pointer back to original so onSegmentSaved can drop it
                text: seg.text || '',
                durationMs: seg.durationMs || 0,
                blob: seg.blob || null,
            });
        }
    });

    const liveText = (liveTranscript || '').trim();
    const liveAlreadyCovered = items.some((i) => (i.text || '').trim() === liveText);
    if (liveText && !liveAlreadyCovered) {
        items.push({ ref: null, text: liveText, durationMs: 0, blob: null });
    }

    if (items.length === 0) return warnings;

    let isFirst = true;
    for (const item of items) {
        let transcriptId;
        try {
            const meta = isFirst ? extractionMeta : null;
            const res = await createTranscript(incidentId, item.text, item.durationMs, meta);
            transcriptId = res.transcriptId;
            isFirst = false;
        } catch (transcriptErr) {
            warnings.push(
                `Voice transcript was not saved: ${transcriptErr.message}.`,
            );
            continue;
        }

        if (AUDIO_ENABLED && item.blob && transcriptId) {
            try {
                await uploadTranscriptAudio(incidentId, transcriptId, item.blob);
            } catch (audioErr) {
                warnings.push(
                    `Audio recording upload failed: ${audioErr.message}. The text transcript was saved.`,
                );
            }
        }

        // Mark this segment as fully done so a retry won't re-create it.
        if (item.ref && onSegmentSaved) {
            try { onSegmentSaved(item.ref); } catch (e) { /* non-fatal */ }
        }
    }

    return warnings;
}
