import React from 'react';
import PropTypes from 'prop-types';
import { Divider, Form, Header } from 'semantic-ui-react';
import CheckboxGroup from '../shared/CheckboxGroup';

const HealthSupportTab = ({ data, onChange, fieldOptions }) => {
  const handleCheckboxChange = (section, key, checked) => {
    onChange({
      ...data,
      [section]: { ...data[section], [key]: checked },
    });
  };

  return (
    <>
      <Header as="h2">Health &amp; Emergency Support</Header>
      <Form size="large">
        <CheckboxGroup
          label="Basic Aid"
          options={fieldOptions.basic_aid || []}
          values={data.basicAid || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('basicAid', key, checked)
          }
        />

        <Divider />

        <CheckboxGroup
          label="Additional Aid"
          options={fieldOptions.additional_aid || []}
          values={data.additionalAid || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('additionalAid', key, checked)
          }
        />

        <Divider />

        <CheckboxGroup
          label="Emergency Services"
          options={fieldOptions.emergency_services || []}
          values={data.emergencyServices || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('emergencyServices', key, checked)
          }
        />
      </Form>
    </>
  );
};

HealthSupportTab.propTypes = {
  data: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.object.isRequired,
};

export default HealthSupportTab;
