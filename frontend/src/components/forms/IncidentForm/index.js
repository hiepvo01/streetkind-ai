import React from 'react';
import PropTypes from 'prop-types';
import {
  Button,
  Divider,
  Form,
  Grid,
  Header,
  Segment,
} from 'semantic-ui-react';
import ClientForm from '../ClientForm';
import EncounteredBySection from './EncounteredBySection';
import OtherServicesSection from './OtherServicesSection';

// ---------------------------------------------------------------------------
// Blank client factory — mirrors ClientFormSchema defaults from client_schema.py
// ---------------------------------------------------------------------------
const createBlankClient = () => ({
  // Section 1: Client Info
  firstName: '',
  lastName: '',
  gender: '',
  ageGroup: '',
  email: '',
  contactNumber: '',
  suburb: '',
  alone: false,

  // Section 1: Risk Assessment
  intoxicationSigns: { speech: false, balance: false, coordination: false, behaviour: false, notVisible: false },
  drugUseSigns: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
  offensiveConduct: { offensiveBehaviour: false, offensiveLanguage: false, obstruction: false, publicDrinking: false, notVisible: false },
  selfHarmSigns: { visibleSigns: false, disclosed: false, notVisible: false },
  suicidalSigns: { ideationObserved: false, ideationDisclosed: false, attemptObserved: false, attemptDisclosed: false, notVisible: false },
  sexualAssault: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
  physicalAssault: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },
  domesticViolence: { observed: false, visibleSigns: false, disclosed: false, notVisible: false },

  // Section 2: Basic Support
  reconnection: { telephone: false, person: false, socialNetwork: false },
  directions: { venue: false, accommodation: false, other: false },
  transportInformation: { bus: false, train: false, taxi: false, uber: false, other: false },
  escortedTo: { accommodation: false, transport: false, friends: false, other: false },
  safeSpace: { escortedTo: false, soberedUp: false },

  // Section 3: Health Support
  basicAid: { vomitBag: false, water: false, footwear: false, lollipop: false },
  additionalAid: { firstAid: false, mentalHealthAid: false },
  emergencyServicesCalled: { ambulanceServiceCalled: false, policeServiceCalled: false, fireServiceCalled: false },

  // Section 4: Risk Minimization
  physicalAssaultRisk: 0,
  sexualAssaultRisk: 0,
  clientConsciousness: 0,
  clientValuablesVisibility: 0,
  clientLostProperty: 0,
  injury: { roadRelated: false, other: false },

  // Section 5: Services Referred
  clientServiceReferrals: {
    alcoholDrugInfoService: false,
    beyondBlue: false,
    childProtectionServices: false,
    dvLine: false,
    hospital: false,
    lifeline: false,
    link2home: false,
    salvosStreetLevel: false,
    streetbeatBus: false,
    traffickingSlaveryAFP: false,
  },
  serviceInformation: { contactedService: false, infoProvided: false },
  otherSupport: { welfareCheck: false, homelessSupport: false },
});

// ---------------------------------------------------------------------------
// IncidentForm
// ---------------------------------------------------------------------------
const IncidentForm = ({ data, onChange, fieldOptions, sites }) => {
  // --- Incident-level field handlers ---
  const handleIncidentChange = (field, value) => {
    onChange({ ...data, incident: { ...data.incident, [field]: value } });
  };

  // --- Encountered-by handler ---
  const handleEncounteredByChange = (updatedEncounteredBy) => {
    onChange({
      ...data,
      incident: { ...data.incident, encounteredBy: updatedEncounteredBy },
    });
  };

  // --- Other-services handler ---
  const handleOtherServicesChange = (updatedOtherServices) => {
    onChange({
      ...data,
      incident: { ...data.incident, otherServices: updatedOtherServices },
    });
  };

  // --- Client handlers ---
  const handleClientChange = (index, updatedClient) => {
    const updatedClients = data.clients.map((c, i) =>
      i === index ? updatedClient : c
    );
    onChange({ ...data, clients: updatedClients });
  };

  const addBlankClient = () => {
    onChange({ ...data, clients: [...data.clients, createBlankClient()] });
  };

  // --- Site options for dropdown ---
  const siteOptions = (sites || []).map((s) => ({
    key: s.key,
    value: s.key,
    text: s.label,
  }));

  const incident = data.incident || {};
  const encounteredBy = incident.encounteredBy || {};
  const otherServices = incident.otherServices || {};

  return (
    <Grid container stackable>
      <Grid.Row>
        <Grid.Column>
          <Header as="h2">Incident Details</Header>
          <Form size="large">
            {/* Row 1: Team Leader, Site, Location */}
            <Form.Group widths={3}>
              <Form.Input
                label="Team Leader Name"
                placeholder="Team leader name"
                value={incident.teamLeaderName || ''}
                onChange={(e, { value }) => handleIncidentChange('teamLeaderName', value)}
              />
              <Form.Select
                label="Base Site"
                placeholder="Select site"
                options={siteOptions}
                value={incident.baseSite || ''}
                onChange={(e, { value }) => handleIncidentChange('baseSite', value)}
              />
              <Form.Input
                label="Location / Address"
                placeholder="Location or address"
                value={incident.location || ''}
                onChange={(e, { value }) => handleIncidentChange('location', value)}
              />
            </Form.Group>

            {/* Row 2: Start and End Times */}
            <Form.Group widths={2}>
              <Form.Input
                label="Incident Start Time"
                type="datetime-local"
                value={incident.startTime || ''}
                onChange={(e, { value }) => handleIncidentChange('startTime', value)}
              />
              <Form.Input
                label="Incident End Time"
                type="datetime-local"
                value={incident.endTime || ''}
                onChange={(e, { value }) => handleIncidentChange('endTime', value)}
              />
            </Form.Group>

            <Divider />

            {/* Encountered By */}
            <Form.Field>
              <label style={{ fontWeight: 'bold', fontSize: '1em' }}>Incident Referred By</label>
            </Form.Field>
            <EncounteredBySection
              data={encounteredBy}
              onChange={handleEncounteredByChange}
              options={fieldOptions.encountered_by || []}
            />

            <Divider />

            {/* Other Services */}
            <Form.Field>
              <label style={{ fontWeight: 'bold', fontSize: '1em' }}>Other Services Referred</label>
            </Form.Field>
            <OtherServicesSection
              data={otherServices}
              onChange={handleOtherServicesChange}
              options={fieldOptions.other_services || []}
            />

            <Divider />

            {/* Clients */}
            <Header as="h2">Clients</Header>
            {(data.clients || []).map((client, i) => (
              <Segment key={i} color="blue">
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
              content="Add Client"
              onClick={addBlankClient}
              type="button"
            />

            <Divider />

            {/* Description and Outcome */}
            <Form.TextArea
              label="Incident Description"
              placeholder="Describe what happened..."
              rows={8}
              value={incident.description || ''}
              onChange={(e, { value }) => handleIncidentChange('description', value)}
            />
            <Form.TextArea
              label="Incident Outcome"
              placeholder="Describe the outcome..."
              rows={8}
              value={incident.outcome || ''}
              onChange={(e, { value }) => handleIncidentChange('outcome', value)}
            />
          </Form>
        </Grid.Column>
      </Grid.Row>
    </Grid>
  );
};

IncidentForm.propTypes = {
  data: PropTypes.shape({
    incident: PropTypes.object.isRequired,
    clients: PropTypes.arrayOf(PropTypes.object).isRequired,
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.object.isRequired,
  sites: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
    })
  ).isRequired,
};

export default IncidentForm;
