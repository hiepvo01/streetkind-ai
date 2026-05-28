/**
 * Merge voice-extracted incident data while preserving volunteer quick notes.
 */
export function mergeExtractedIncident(prev, extracted) {
  const quickNote = prev?.incident?.quickNote ?? '';
  return {
    ...extracted,
    incident: {
      ...extracted.incident,
      quickNote,
    },
  };
}
