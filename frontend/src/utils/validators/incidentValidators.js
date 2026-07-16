/**
 * Incident-level required-field validation for the "Confirm & Submit" gate.
 * Returns a { field: message } map (empty object = valid). Draft saves do NOT
 * call this - drafts may be incomplete.
 *
 * Keep this in sync with the backend mirror in
 * app/services/incident_completeness.py.
 */

export const REQUIRED_MSG = 'Required';
export const END_AFTER_START_MSG = 'End time must be after start time';

export function validateIncident(incident = {}) {
  const errors = {};

  if (!(incident.teamLeaderName || '').trim()) errors.teamLeaderName = REQUIRED_MSG;
  if (!incident.site) errors.site = REQUIRED_MSG;
  if (incident.startTime === null || incident.startTime === undefined) {
    errors.startTime = REQUIRED_MSG;
  }
  if (incident.endTime === null || incident.endTime === undefined) {
    errors.endTime = REQUIRED_MSG;
  } else if (
    incident.startTime !== null
    && incident.startTime !== undefined
    && incident.endTime <= incident.startTime
  ) {
    errors.endTime = END_AFTER_START_MSG;
  }
  if (!(incident.incidentDescription || '').trim()) errors.incidentDescription = REQUIRED_MSG;
  if (!(incident.incidentOutcome || '').trim()) errors.incidentOutcome = REQUIRED_MSG;

  return errors;
}
