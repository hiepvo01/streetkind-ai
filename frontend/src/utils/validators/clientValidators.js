/**
 * Per-client required-field validation for the "Confirm & Submit" gate, plus a
 * top-level aggregator over the whole incident form. Returns { field: message }
 * maps (empty = valid). Draft saves do NOT call these.
 *
 * Keep the required list and SIGN_GROUPS in sync with the backend mirror in
 * app/services/incident_completeness.py.
 */

import { validateIncident, REQUIRED_MSG } from './incidentValidators';

export const TRISTATE_MSG = "Tick either 'Not Visible' or the others.";

/**
 * The 8 tri-state "signs" groups. `others` are the sub-fields that count as a
 * positive indicator; every group also has an implicit `notVisible` sub-field.
 * Keys mirror app/schemas/client_schema.py.
 */
export const SIGN_GROUPS = [
  { key: 'intoxicationSigns', others: ['speech', 'balance', 'coordination', 'behaviour'] },
  { key: 'drugUseSigns', others: ['observed', 'visibleSigns', 'disclosed'] },
  { key: 'offensiveConduct', others: ['offensiveBehaviour', 'offensiveLanguage', 'obstruction', 'publicDrinking'] },
  { key: 'selfHarmSigns', others: ['visibleSigns', 'disclosed'] },
  { key: 'suicidalSigns', others: ['ideationObserved', 'ideationDisclosed', 'attemptObserved', 'attemptDisclosed'] },
  { key: 'sexualAssault', others: ['observed', 'visibleSigns', 'disclosed'] },
  { key: 'physicalAssault', others: ['observed', 'visibleSigns', 'disclosed'] },
  { key: 'domesticViolence', others: ['observed', 'visibleSigns', 'disclosed'] },
];

export function validateClient(client = {}) {
  const errors = {};

  if (!client.gender) errors.gender = REQUIRED_MSG;
  if (!client.ageGroup) errors.ageGroup = REQUIRED_MSG;
  if (client.alone === null || client.alone === undefined) errors.alone = REQUIRED_MSG;

  for (const { key, others } of SIGN_GROUPS) {
    const group = client[key] || {};
    const anyOther = others.some((k) => group[k]);
    if (!group.notVisible && !anyOther) {
      errors[key] = REQUIRED_MSG;
    } else if (group.notVisible && anyOther) {
      errors[key] = TRISTATE_MSG;
    }
  }

  return errors;
}

/**
 * Validate the whole incident form (incident + every client).
 * Returns { incident: {...}, clients: [{...}, ...], hasErrors: bool }.
 */
export function validateIncidentForm(data = {}) {
  const incident = validateIncident(data.incident || {});
  const clients = (data.clients || []).map(validateClient);

  const hasErrors = Object.keys(incident).length > 0
    || clients.some((c) => Object.keys(c).length > 0);

  return { incident, clients, hasErrors };
}
