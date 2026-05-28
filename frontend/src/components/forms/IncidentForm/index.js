import React, { useRef, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Button,
  Divider,
  Form,
  Header,
  Message,
  Popup,
  Segment,
} from 'semantic-ui-react';
import ClientForm from '../ClientForm';
import EncounteredBySection from './EncounteredBySection';
import OtherServicesSection from './OtherServicesSection';
import LocationMapModal from './LocationMapModal';
import QuickNoteFab from './QuickNoteFab';
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
  const containerRef = useRef(null);
  const [magicLoading, setMagicLoading] = useState(false);
  const [magicCooldown, setMagicCooldown] = useState(false);
  const [magicError, setMagicError] = useState(null);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState(null);
  const [locationChoiceOpen, setLocationChoiceOpen] = useState(false);
  const [mapModalOpen, setMapModalOpen] = useState(false);

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

  const applyLocationFromCoords = async (lat, lon) => {
    setGeoError(null);
    setGeoLoading(true);
    try {
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
      setGeoError(e?.message || 'Failed to resolve address from location.');
    } finally {
      setGeoLoading(false);
    }
  };

  const handleUseCurrentLocation = async () => {
    setLocationChoiceOpen(false);
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

      await applyLocationFromCoords(lat, lon);
    } catch (e) {
      const msg =
        e?.code === 1 ? 'Location permission denied.' :
        e?.code === 2 ? 'Location unavailable.' :
        e?.code === 3 ? 'Location request timed out.' :
        (e?.message || 'Failed to use location.');
      setGeoError(msg);
      setGeoLoading(false);
    }
  };

  const handlePickOnMap = () => {
    setLocationChoiceOpen(false);
    setMapModalOpen(true);
  };

  const handleMapConfirm = async ({ lat, lon }) => {
    await applyLocationFromCoords(lat, lon);
    setMapModalOpen(false);
  };

  const mapInitialLat =
    typeof location.latitude === 'number' ? location.latitude : null;
  const mapInitialLon =
    typeof location.longitude === 'number' ? location.longitude : null;

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
    <div ref={containerRef}>
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
            <Popup
              on="click"
              open={locationChoiceOpen}
              onOpen={() => setLocationChoiceOpen(true)}
              onClose={() => setLocationChoiceOpen(false)}
              position="bottom left"
              wide
              disabled={geoLoading}
              trigger={
                <Button
                  type="button"
                  icon="location arrow"
                  content="Use my location"
                  loading={geoLoading}
                  disabled={geoLoading}
                  style={{ marginBottom: '3rem' }}
                />
              }
              content={
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <Button
                    type="button"
                    icon="crosshairs"
                    content="Use current location"
                    onClick={handleUseCurrentLocation}
                    disabled={geoLoading}
                  />
                  <Button
                    type="button"
                    icon="map"
                    content="Pick on map"
                    onClick={handlePickOnMap}
                    disabled={geoLoading}
                  />
                </div>
              }
            />
            <LocationMapModal
              open={mapModalOpen}
              onClose={() => setMapModalOpen(false)}
              initialLat={mapInitialLat}
              initialLon={mapInitialLon}
              onConfirm={handleMapConfirm}
              loading={geoLoading}
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
      <QuickNoteFab
        containerRef={containerRef}
        value={incident.quickNote || ''}
        onChange={(v) => handleIncidentField('quickNote', v)}
      />
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
