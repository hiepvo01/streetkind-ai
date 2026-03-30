import React from 'react';
import PropTypes from 'prop-types';
import { Divider, Form, Grid, Header } from 'semantic-ui-react';
import CheckboxGroup from '../shared/CheckboxGroup';
import RadioGroup from '../shared/RadioGroup';

const ALONE_OPTIONS = [
  { value: true, label: 'Yes' },
  { value: false, label: 'No' },
];

const ClientInfoTab = ({ data, onChange, fieldOptions }) => {
  const mapKeysToValues = (options) =>
    (options || []).map((opt) => ({ value: opt.key, label: opt.label }));

  const handleRadioChange = (field, value) => {
    onChange({ ...data, [field]: value });
  };

  const handleCheckboxChange = (section, key, checked) => {
    onChange({
      ...data,
      [section]: { ...data[section], [key]: checked },
    });
  };

  const handleInputChange = (field, value) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <>
      <Header as="h2">Client Information</Header>
      <Form size="large">
        <Grid columns="equal" stackable celled="internally">
          <Grid.Column mobile={16} tablet={8} computer={4}>
            <RadioGroup
              label="Gender"
              options={mapKeysToValues(fieldOptions.gender)}
              value={data.gender}
              onChange={(val) => handleRadioChange('gender', val)}
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={8} computer={4}>
            <RadioGroup
              label="Age Group"
              options={mapKeysToValues(fieldOptions.age_group)}
              value={data.ageGroup}
              onChange={(val) => handleRadioChange('ageGroup', val)}
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={8} computer={4}>
            <RadioGroup
              label="Alone"
              options={ALONE_OPTIONS}
              value={data.alone}
              onChange={(val) => handleRadioChange('alone', val)}
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={8} computer={4}>
            <CheckboxGroup
              label="Intoxication Signs"
              options={fieldOptions.intoxication_signs || []}
              values={data.intoxicationSigns || {}}
              onChange={(key, checked) =>
                handleCheckboxChange('intoxicationSigns', key, checked)
              }
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={8} computer={4}>
            <CheckboxGroup
              label="Drug Use Signs"
              options={fieldOptions.drug_use_signs || []}
              values={data.drugUseSigns || {}}
              onChange={(key, checked) =>
                handleCheckboxChange('drugUseSigns', key, checked)
              }
            />
          </Grid.Column>
        </Grid>

        <Divider />

        <Grid columns="equal" stackable celled="internally">
          <Grid.Column mobile={16} tablet={8} computer={5}>
            <CheckboxGroup
              label="Offensive Conduct"
              options={fieldOptions.offensive_conduct || []}
              values={data.offensiveConduct || {}}
              onChange={(key, checked) =>
                handleCheckboxChange('offensiveConduct', key, checked)
              }
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={8} computer={5}>
            <CheckboxGroup
              label="Self Harm Signs"
              options={fieldOptions.self_harm_signs || []}
              values={data.selfHarmSigns || {}}
              onChange={(key, checked) =>
                handleCheckboxChange('selfHarmSigns', key, checked)
              }
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={8} computer={5}>
            <CheckboxGroup
              label="Suicidal Signs"
              options={fieldOptions.suicidal_signs || []}
              values={data.suicidalSigns || {}}
              onChange={(key, checked) =>
                handleCheckboxChange('suicidalSigns', key, checked)
              }
            />
          </Grid.Column>
        </Grid>

        <Divider />

        <Grid columns={3} stackable celled="internally">
          <Grid.Column mobile={16} tablet={8} computer={5}>
            <CheckboxGroup
              label="Sexual Assault"
              options={fieldOptions.assault_indicators || []}
              values={data.sexualAssault || {}}
              onChange={(key, checked) =>
                handleCheckboxChange('sexualAssault', key, checked)
              }
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={8} computer={5}>
            <CheckboxGroup
              label="Physical Assault"
              options={fieldOptions.assault_indicators || []}
              values={data.physicalAssault || {}}
              onChange={(key, checked) =>
                handleCheckboxChange('physicalAssault', key, checked)
              }
            />
          </Grid.Column>
          <Grid.Column mobile={16} tablet={8} computer={5}>
            <CheckboxGroup
              label="Domestic Violence"
              options={fieldOptions.assault_indicators || []}
              values={data.domesticViolence || {}}
              onChange={(key, checked) =>
                handleCheckboxChange('domesticViolence', key, checked)
              }
            />
          </Grid.Column>
        </Grid>

        <Divider />

        <Form.Field label="Contact Information" />
        <Form.Group widths={2}>
          <Form.Input
            label="First Name"
            placeholder="First Name"
            value={data.firstName || ''}
            onChange={(e, { value }) => handleInputChange('firstName', value)}
          />
          <Form.Input
            label="Suburb"
            placeholder="Suburb"
            value={data.suburb || ''}
            onChange={(e, { value }) => handleInputChange('suburb', value)}
          />
        </Form.Group>
      </Form>
    </>
  );
};

ClientInfoTab.propTypes = {
  data: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.object.isRequired,
};

export default ClientInfoTab;
