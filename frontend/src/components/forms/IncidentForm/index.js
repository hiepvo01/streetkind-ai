import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Button,
  Divider,
  Form,
  Header,
  Message,
  Segment,
} from 'semantic-ui-react';
import ClientForm from '../ClientForm';
import EncounteredBySection from './EncounteredBySection';
import OtherServicesSection from './OtherServicesSection';
import { createBlankClient } from '../../../utils/initialFormData';
import { generateIncidentNarrative, reverseGeocode } from '../../../services/api';

const NARRATIVE_OVERWRITE_CONFIRM_LEN = 40;
/** Brief client-side cooldown after a successful Magic call to reduce double-clicks (backend still enforces per-minute cap). */
const MAGIC_CLIENT_COOLDOWN_MS = 8000;

const hasSubstantialNarrativeText = (inc) => {
  const d = (inc.incidentDescription || '').trim();
  const o = (inc.incidentOutcome || '').trim();
  return d.length > NARRATIVE_OVERWRITE_CONFIRM_LEN || o.length > NARRATIVE_OVERWRITE_CONFIRM_LEN;
};

// ---------------------------------------------------------------------------
// IncidentForm — matches SKSSIR IncidentForm.js field names exactly
// ---------------------------------------------------------------------------
const IncidentForm = ({ data, onChange, fieldOptions, sites }) => {
  // data = { incident: {...}, clients: [...] }
  const [magicLoading, setMagicLoading] = useState(false);
  const [magicCooldown, setMagicCooldown] = useState(false);
  const [magicError, setMagicError] = useState(null);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState(null);

  const incident = data.incident || {};
  const clients = data.clients || [];
  const location = incident.location || {};
  const encounteredBy = incident.encounteredBy || {};
  const otherServicesInvolved = incident.otherServicesInvolved || {};

  const handleIncidentField = (field, value) => {
    onChange({ ...data, incident: { ...incident, [field]: value } });
  };

  const handleLocationChange = (value) => {
    onChange({
      ...data,
      incident: { ...incident, location: { ...location, address: value } },
    });
  };

  const handleUseMyLocation = async () => {
    setGeoError(null);
    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported in this browser.');
      return;
    }
    setGeoLoading(true);
    try {
      const pos = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000,
        });
      });

      const lat = pos?.coords?.latitude;
      const lon = pos?.coords?.longitude;
      if (typeof lat !== 'number' || typeof lon !== 'number') {
        throw new Error('Could not read coordinates from your device.');
      }

      const res = await reverseGeocode(lat, lon);
      const typedAddress = (location.address || '').trim();
      const resolvedAddress = (res.address || '').trim();
      if (typedAddress && resolvedAddress) {
        const ok = window.confirm(
          'Replace the current address with the address detected from your location?'
        );
        if (!ok) {
          return;
        }
      }
      onChange({
        ...data,
        incident: {
          ...incident,
          location: {
            ...location,
            address: resolvedAddress || typedAddress || location.address || '',
            latitude: res.latitude ?? lat,
            longitude: res.longitude ?? lon,
          },
        },
      });
    } catch (e) {
      const msg =
        e?.code === 1 ? 'Location permission denied.' :
        e?.code === 2 ? 'Location unavailable.' :
        e?.code === 3 ? 'Location request timed out.' :
        (e?.message || 'Failed to use location.');
      setGeoError(msg);
    } finally {
      setGeoLoading(false);
    }
  };

  const handleEncounteredByChange = (updated) => {
    onChange({ ...data, incident: { ...incident, encounteredBy: updated } });
  };

  const handleOtherServicesChange = (updated) => {
    onChange({ ...data, incident: { ...incident, otherServicesInvolved: updated } });
  };

  const handleClientChange = (index, updatedClient) => {
    const updatedClients = clients.map((c, i) => (i === index ? updatedClient : c));
    onChange({ ...data, clients: updatedClients });
  };

  const handleRemoveClient = (index) => {
    onChange({ ...data, clients: clients.filter((_, i) => i !== index) });
  };

  const addBlankClient = () => {
    onChange({ ...data, clients: [...clients, createBlankClient()] });
  };

  const handleMagicGenerate = async () => {
    setMagicError(null);
    if (hasSubstantialNarrativeText(incident)) {
      const ok = window.confirm(
        'Replace existing incident description and outcome with AI-generated drafts? You can still edit them afterwards.'
      );
      if (!ok) return;
    }
    setMagicLoading(true);
    try {
      const draft = await generateIncidentNarrative(data);
      onChange({
        ...data,
        incident: {
          ...incident,
          incidentDescription: draft.incidentDescription ?? '',
          incidentOutcome: draft.incidentOutcome ?? '',
        },
      });
      setMagicCooldown(true);
      setTimeout(() => setMagicCooldown(false), MAGIC_CLIENT_COOLDOWN_MS);
    } catch (e) {
      setMagicError(e.message || 'Generation failed');
    } finally {
      setMagicLoading(false);
    }
  };

  const siteOptions = (sites || []).map((s) => ({
    key: s.key,
    value: s.key,
    text: s.label,
  }));

  const createdAtLabel = (() => {
    const ts = incident.createdDate || incident.startTime;
    if (!ts) return '—';
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString('en-AU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  })();

  return (
    <div>
      <Header as="h2">Incident Details</Header>
      <Form size="large">
        <Form.Group widths="equal">
              <Form.Input
                label="Team Leader Name"
                placeholder="Team leader name"
                value={incident.teamLeaderName || ''}
                onChange={(e, { value }) => handleIncidentField('teamLeaderName', value)}
              />
              <Form.Select
                label="Base Site"
                placeholder="Select site"
                options={siteOptions}
                value={incident.site || ''}
                onChange={(e, { value }) => handleIncidentField('site', value)}
              />
              <Form.Input
                label="Location / Address"
                placeholder="Location or address"
                value={location.address || ''}
                onChange={(e, { value }) => handleLocationChange(value)}
              />
            </Form.Group>
            {geoError && (
              <Message
                error
                content={geoError}
                onDismiss={() => setGeoError(null)}
              />
            )}
            <Button
              type="button"
              icon="location arrow"
              content="Use my location"
              loading={geoLoading}
              disabled={geoLoading}
              onClick={handleUseMyLocation}
              style={{ marginBottom: '3rem' }}
            />
            <Form.Field style={{ marginTop: '0.25rem', marginBottom: '1rem' }}>
              <label>Date/Time (Created)</label>
              <div style={{ color: 'rgba(0,0,0,0.6)' }}>{createdAtLabel}</div>
            </Form.Field>

            <Divider />

            <Form.Field>
              <label style={{ fontWeight: 'bold', fontSize: '1em' }}>Incident Referred By</label>
            </Form.Field>
            <EncounteredBySection
              data={encounteredBy}
              onChange={handleEncounteredByChange}
              options={fieldOptions.encountered_by || []}
            />

            <Divider />

            <Form.Field>
              <label style={{ fontWeight: 'bold', fontSize: '1em' }}>Other Services Referred</label>
            </Form.Field>
            <OtherServicesSection
              data={otherServicesInvolved}
              onChange={handleOtherServicesChange}
              options={fieldOptions.other_services || []}
            />

            <Divider />

            <Header as="h2">
              Clients ({clients.length})
            </Header>
            {clients.map((client, i) => (
              <Segment key={i} color="blue" raised>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5em' }}>
                  <Header as="h3" style={{ margin: 0 }}>Client {i + 1}</Header>
                  <Button
                    color="red"
                    size="mini"
                    icon="trash"
                    content="Remove"
                    type="button"
                    onClick={() => handleRemoveClient(i)}
                  />
                </div>
                <ClientForm
                  data={client}
                  onChange={(updatedClient) => handleClientChange(i, updatedClient)}
                  fieldOptions={fieldOptions}
                />
              </Segment>
            ))}
            <Button
              color="blue"
              icon="add user"
              labelPosition="left"
              content="Add Client"
              onClick={addBlankClient}
              type="button"
              style={{ marginTop: '0.5em' }}
            />

            <Divider />

            <Form.TextArea
              label="Quick note"
              placeholder="Short notes for context (saved with the incident; used when generating narrative)"
              rows={4}
              value={incident.quickNote || ''}
              onChange={(e, { value }) => handleIncidentField('quickNote', value)}
            />
            {magicError && (
              <Message
                error
                content={magicError}
                onDismiss={() => setMagicError(null)}
              />
            )}
            <Button
              type="button"
              color="violet"
              icon="magic"
              labelPosition="left"
              content="Magic generate (description & outcome)"
              loading={magicLoading}
              disabled={magicLoading || magicCooldown}
              onClick={handleMagicGenerate}
              style={{ marginBottom: '1rem' }}
            />
            <Form.TextArea
              label="Incident Description"
              placeholder="Describe what happened..."
              rows={8}
              value={incident.incidentDescription || ''}
              onChange={(e, { value }) => handleIncidentField('incidentDescription', value)}
            />
            <Form.TextArea
              label="Incident Outcome"
              placeholder="Describe the outcome..."
              rows={8}
              value={incident.incidentOutcome || ''}
              onChange={(e, { value }) => handleIncidentField('incidentOutcome', value)}
            />
      </Form>
    </div>
  );
};

IncidentForm.propTypes = {
  data: PropTypes.shape({
    incident: PropTypes.object,
    clients: PropTypes.arrayOf(PropTypes.object),
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.object.isRequired,
  sites: PropTypes.array.isRequired,
};

export default IncidentForm;
