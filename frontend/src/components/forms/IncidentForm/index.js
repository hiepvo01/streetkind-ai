import React from 'react';
import PropTypes from 'prop-types';
import {
  Button,
  Divider,
  Form,
  Header,
  Segment,
} from 'semantic-ui-react';
import ClientForm from '../ClientForm';
import EncounteredBySection from './EncounteredBySection';
import OtherServicesSection from './OtherServicesSection';

// ---------------------------------------------------------------------------
// Blank client factory — mirrors ClientFormSchema defaults
// ---------------------------------------------------------------------------
const createBlankClient = () => ({
  firstName: '',
  lastName: '',
  gender: '',
  ageGroup: '',
  email: '',
  contactNumber: '',
  suburb: '',
  alone: false,
  intoxicationSigns: { speech: false, balance: false, coordination: false, behaviour: false, notVisible: false },
  drugUseSigns: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
  offensiveConduct: { offensiveBehaviour: false, offensiveLanguage: false, obstruction: false, publicDrinking: false, notVisible: false },
  selfHarmSigns: { visibleSigns: false, disclosed: false, notVisible: false },
  suicidalSigns: { ideationObserved: false, ideationDisclosed: false, attemptObserved: false, attemptDisclosed: false, notVisible: false },
  sexualAssault: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
  physicalAssault: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
  domesticViolence: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
  reconnection: { telephone: false, person: false, socialNetwork: false },
  directions: { venue: false, accommodation: false, other: false },
  transportInformation: { bus: false, train: false, taxi: false, uber: false, other: false },
  escortedTo: { accommodation: false, transport: false, friends: false, other: false },
  safeSpace: { escortedTo: false, soberedUp: false },
  basicAid: { vomitBag: false, water: false, footwear: false, lollipop: false },
  additionalAid: { firstAid: false, mentalHealthAid: false },
  emergencyServicesCalled: { ambulanceServiceCalled: false, policeServiceCalled: false, fireServiceCalled: false },
  physicalAssaultRisk: 0,
  sexualAssaultRisk: 0,
  clientConsciousness: 0,
  clientValuablesVisibility: 0,
  clientLostProperty: 0,
  injury: { roadRelated: false, other: false },
  clientServiceReferrals: {
    alcoholDrugInfoService: false, beyondBlue: false, childProtectionServices: false,
    dvLine: false, hospital: false, lifeline: false, link2home: false,
    salvosStreetLevel: false, streetbeatBus: false, traffickingSlaveryAFP: false,
  },
  serviceInformation: { contactedService: false, infoProvided: false },
  otherSupport: { welfareCheck: false, homelessSupport: false },
});

// ---------------------------------------------------------------------------
// IncidentForm — matches SKSSIR IncidentForm.js field names exactly
// ---------------------------------------------------------------------------
const IncidentForm = ({ data, onChange, fieldOptions, sites }) => {
  // data = { incident: {...}, clients: [...] }
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

  const siteOptions = (sites || []).map((s) => ({
    key: s.key,
    value: s.key,
    text: s.label,
  }));

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
                  clientIndex={i}
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
