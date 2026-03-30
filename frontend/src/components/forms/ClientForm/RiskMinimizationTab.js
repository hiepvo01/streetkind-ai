import React from 'react';
import PropTypes from 'prop-types';
import { Divider, Form, Grid, Header } from 'semantic-ui-react';
import RadioGroup from '../shared/RadioGroup';
import CheckboxGroup from '../shared/CheckboxGroup';

const PHYSICAL_ASSAULT_RISK_OPTIONS = [
  { value: 0, label: 'No Risk' },
  { value: 1, label: 'At Risk of Violent Assault' },
  { value: 2, label: 'Minor Conflict De-escalated' },
  { value: 3, label: 'Major Conflict De-escalated' },
];

const SEXUAL_ASSAULT_RISK_OPTIONS = [
  { value: 0, label: 'No Risk' },
  { value: 1, label: 'At Risk of Sexual Assault' },
  { value: 2, label: 'Minor Assault Risk' },
  { value: 3, label: 'Major Assault Risk' },
];

const CLIENT_CONSCIOUSNESS_OPTIONS = [
  { value: 0, label: 'Conscious' },
  { value: 1, label: 'Unconscious' },
  { value: 2, label: 'Asleep' },
  { value: 3, label: 'Passed Out' },
];

const VALUABLES_VISIBILITY_OPTIONS = [
  { value: 0, label: 'Not Visible' },
  { value: 1, label: 'Visible' },
];

const LOST_PROPERTY_OPTIONS = [
  { value: 0, label: 'No Lost Property' },
  { value: 1, label: 'Valuables Lost and Found' },
  { value: 2, label: 'Valuables Lost' },
];

const INJURY_RISK_OPTIONS = [
  { key: 'roadRelated', label: 'Road Related' },
  { key: 'other', label: 'Other' },
];

const RiskMinimizationTab = ({ data, onChange, fieldOptions }) => {
  const handleRadioChange = (field, value) => {
    onChange({ ...data, [field]: value });
  };

  const handleNestedRadioChange = (section, field, value) => {
    onChange({
      ...data,
      [section]: { ...data[section], [field]: value },
    });
  };

  const handleCheckboxChange = (section, key, checked) => {
    onChange({
      ...data,
      [section]: { ...data[section], [key]: checked },
    });
  };

  const theftRisk = data.theftRisk || {};

  return (
    <>
      <Header as="h2">Risk Minimisation</Header>
      <Form size="large">
        <RadioGroup
          label="Physical Assault Risk"
          options={PHYSICAL_ASSAULT_RISK_OPTIONS}
          value={data.physicalAssaultRisk}
          onChange={(val) => handleRadioChange('physicalAssaultRisk', val)}
        />

        <Divider />

        <RadioGroup
          label="Sexual Assault Risk"
          options={SEXUAL_ASSAULT_RISK_OPTIONS}
          value={data.sexualAssaultRisk}
          onChange={(val) => handleRadioChange('sexualAssaultRisk', val)}
        />

        <Divider />

        <Form.Field label="Theft Risk" />
        <Grid stackable>
          <Grid.Row columns="equal">
            <Grid.Column mobile={16} tablet={8} computer={5}>
              <RadioGroup
                label="Client Consciousness"
                options={CLIENT_CONSCIOUSNESS_OPTIONS}
                value={theftRisk.clientConsciousness}
                onChange={(val) =>
                  handleNestedRadioChange('theftRisk', 'clientConsciousness', val)
                }
              />
            </Grid.Column>
            <Grid.Column mobile={16} tablet={8} computer={5}>
              <RadioGroup
                label="Valuables Visibility"
                options={VALUABLES_VISIBILITY_OPTIONS}
                value={theftRisk.valuablesVisibility}
                onChange={(val) =>
                  handleNestedRadioChange('theftRisk', 'valuablesVisibility', val)
                }
              />
            </Grid.Column>
            <Grid.Column mobile={16} tablet={8} computer={5}>
              <RadioGroup
                label="Lost Property"
                options={LOST_PROPERTY_OPTIONS}
                value={theftRisk.lostProperty}
                onChange={(val) =>
                  handleNestedRadioChange('theftRisk', 'lostProperty', val)
                }
              />
            </Grid.Column>
          </Grid.Row>
        </Grid>

        <Divider />

        <CheckboxGroup
          label="Injury Risk"
          options={INJURY_RISK_OPTIONS}
          values={data.injuryRisk || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('injuryRisk', key, checked)
          }
        />
      </Form>
    </>
  );
};

RiskMinimizationTab.propTypes = {
  data: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.object.isRequired,
};

export default RiskMinimizationTab;
