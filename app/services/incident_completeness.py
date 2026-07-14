"""
Server-side required-field validation for a COMPLETED incident submission.

This is the authoritative enforcement (the frontend does the same checks for
UX, but that can be bypassed by calling the API directly). Only applied when
status == "completed"; drafts are allowed to be incomplete.

Keep the rules in sync with the frontend mirror:
  frontend/src/utils/validators/incidentValidators.js
  frontend/src/utils/validators/clientValidators.js
"""

from ..schemas.combined_incident_schema import CombinedIncidentSchema

# The 8 tri-state "signs" groups: (attribute, [positive sub-fields]). Every group
# also has an implicit `notVisible` sub-field. Mirrors client_schema.py.
SIGN_GROUPS = [
    ("intoxicationSigns", ["speech", "balance", "coordination", "behaviour"]),
    ("drugUseSigns", ["observed", "visibleSigns", "disclosed"]),
    ("offensiveConduct", ["offensiveBehaviour", "offensiveLanguage", "obstruction", "publicDrinking"]),
    ("selfHarmSigns", ["visibleSigns", "disclosed"]),
    ("suicidalSigns", ["ideationObserved", "ideationDisclosed", "attemptObserved", "attemptDisclosed"]),
    ("sexualAssault", ["observed", "visibleSigns", "disclosed"]),
    ("physicalAssault", ["observed", "visibleSigns", "disclosed"]),
    ("domesticViolence", ["observed", "visibleSigns", "disclosed"]),
]


def _check_incident(incident) -> list[str]:
    errors = []
    if not (incident.teamLeaderName or "").strip():
        errors.append("incident.teamLeaderName: Required")
    if not incident.site:
        errors.append("incident.site: Required")
    if incident.startTime is None:
        errors.append("incident.startTime: Required")
    if incident.endTime is None:
        errors.append("incident.endTime: Required")
    elif incident.startTime is not None and incident.endTime <= incident.startTime:
        errors.append("incident.endTime: End time must be after start time")
    if not (incident.incidentDescription or "").strip():
        errors.append("incident.incidentDescription: Required")
    if not (incident.incidentOutcome or "").strip():
        errors.append("incident.incidentOutcome: Required")
    return errors


def _check_client(client, index: int) -> list[str]:
    errors = []
    prefix = f"clients[{index}]"
    if not client.gender:
        errors.append(f"{prefix}.gender: Required")
    if not client.ageGroup:
        errors.append(f"{prefix}.ageGroup: Required")
    if client.alone is None:
        errors.append(f"{prefix}.alone: Required")

    for attr, others in SIGN_GROUPS:
        group = getattr(client, attr)
        any_other = any(getattr(group, k) for k in others)
        not_visible = getattr(group, "notVisible")
        if not not_visible and not any_other:
            errors.append(f"{prefix}.{attr}: Required")
        elif not_visible and any_other:
            errors.append(f"{prefix}.{attr}: Tick either 'Not Visible' or the others.")
    return errors


def check_incident_complete(combined: CombinedIncidentSchema) -> list[str]:
    """
    Return a list of human-readable completeness errors for a combined incident.
    Empty list means the incident is complete enough to submit as "completed".
    """
    errors = _check_incident(combined.incident)
    for i, client in enumerate(combined.clients):
        errors.extend(_check_client(client, i))
    return errors
