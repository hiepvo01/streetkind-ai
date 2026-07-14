import React from 'react';
import PropTypes from 'prop-types';
import { Divider, Form, Grid, Header } from 'semantic-ui-react';
import CheckboxGroup from '../shared/CheckboxGroup';
import RadioGroup from '../shared/RadioGroup';

const ALONE_OPTIONS = [
  { value: true, label: 'Yes' },
  { value: false, label: 'No' },
];

const ClientInfoTab = ({ data, onChange, fieldOptions, errors, showErrors }) => {
  const mapKeysToValues = (options) =>
    (options || []).map((opt) => ({ value: opt.key, label: opt.label }));

  // Errors only surface after a failed submit.
  const err = showErrors ? errors : {};

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
      <Header as="h3">Client Information</Header>
      <Form size="large">
        {/* Row 1: Demographics */}
        <Grid stackable>
          <Grid.Row columns={3}>
            <Grid.Column mobile={16} tablet={5} computer={5}>
              <RadioGroup
                label="Gender"
                required
                error={err.gender}
                options={mapKeysToValues(fieldOptions.gender)}
                value={data.gender}
                onChange={(val) => handleRadioChange('gender', val)}
              />
            </Grid.Column>
            <Grid.Column mobile={16} tablet={5} computer={5}>
              <RadioGroup
                label="Age Group"
                required
                error={err.ageGroup}
                options={mapKeysToValues(fieldOptions.age_group)}
                value={data.ageGroup}
                onChange={(val) => handleRadioChange('ageGroup', val)}
              />
            </Grid.Column>
            <Grid.Column mobile={16} tablet={5} computer={5}>
              <RadioGroup
                label="Alone"
                required
                error={err.alone}
                options={ALONE_OPTIONS}
                value={data.alone}
                onChange={(val) => handleRadioChange('alone', val)}
              />
            </Grid.Column>
          </Grid.Row>
        </Grid>

        <Divider />

        {/* Row 2: Intoxication & Drug */}
        <Grid stackable>
          <Grid.Row columns={2}>
            <Grid.Column mobile={16} tablet={8} computer={8}>
              <CheckboxGroup
                label="Intoxication Signs"
                required
                error={err.intoxicationSigns}
                options={fieldOptions.intoxication_signs || []}
                values={data.intoxicationSigns || {}}
                onChange={(key, checked) =>
                  handleCheckboxChange('intoxicationSigns', key, checked)
                }
              />
            </Grid.Column>
            <Grid.Column mobile={16} tablet={8} computer={8}>
              <CheckboxGroup
                label="Drug Use Signs"
                required
                error={err.drugUseSigns}
                options={fieldOptions.drug_use_signs || []}
                values={data.drugUseSigns || {}}
                onChange={(key, checked) =>
                  handleCheckboxChange('drugUseSigns', key, checked)
                }
              />
            </Grid.Column>
          </Grid.Row>
        </Grid>

        <Divider />

        {/* Row 3: Conduct & Harm */}
        <Grid stackable>
          <Grid.Row columns={3}>
            <Grid.Column mobile={16} tablet={8} computer={5}>
              <CheckboxGroup
                label="Offensive Conduct"
                required
                error={err.offensiveConduct}
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
                required
                error={err.selfHarmSigns}
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
                required
                error={err.suicidalSigns}
                options={fieldOptions.suicidal_signs || []}
                values={data.suicidalSigns || {}}
                onChange={(key, checked) =>
                  handleCheckboxChange('suicidalSigns', key, checked)
                }
              />
            </Grid.Column>
          </Grid.Row>
        </Grid>

        <Divider />

        {/* Row 4: Assault & DV */}
        <Grid stackable>
          <Grid.Row columns={3}>
            <Grid.Column mobile={16} tablet={8} computer={5}>
              <CheckboxGroup
                label="Sexual Assault"
                required
                error={err.sexualAssault}
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
                required
                error={err.physicalAssault}
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
                required
                error={err.domesticViolence}
                options={fieldOptions.assault_indicators || []}
                values={data.domesticViolence || {}}
                onChange={(key, checked) =>
                  handleCheckboxChange('domesticViolence', key, checked)
                }
              />
            </Grid.Column>
          </Grid.Row>
        </Grid>

        <Divider />

        {/* Contact Info */}
        <Form.Field><label style={{ fontWeight: 'bold' }}>Contact Information</label></Form.Field>
        <Form.Group widths="equal">
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
  errors: PropTypes.object,
  showErrors: PropTypes.bool,
};

ClientInfoTab.defaultProps = {
  errors: {},
  showErrors: false,
};

export default ClientInfoTab;
