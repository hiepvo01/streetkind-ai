import React from 'react';
import PropTypes from 'prop-types';
import { Divider, Form, Header } from 'semantic-ui-react';
import CheckboxGroup from '../shared/CheckboxGroup';

const SAFE_SPACE_OPTIONS = [
  { key: 'escortedTo', label: 'Escorted to Safe Base' },
  { key: 'soberedUp', label: 'Sobered Up at Safe Base' },
];

const BasicSupportTab = ({ data, onChange, fieldOptions }) => {
  const handleCheckboxChange = (section, key, checked) => {
    onChange({
      ...data,
      [section]: { ...data[section], [key]: checked },
    });
  };

  return (
    <>
      <Header as="h2">Basic Support</Header>
      <Form size="large">
        <CheckboxGroup
          label="Reconnection"
          options={fieldOptions.reconnection || []}
          values={data.reconnection || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('reconnection', key, checked)
          }
        />

        <Divider />

        <CheckboxGroup
          label="Directions"
          options={fieldOptions.directions || []}
          values={data.directions || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('directions', key, checked)
          }
        />

        <Divider />

        <CheckboxGroup
          label="Transport Information"
          options={fieldOptions.transport_information || []}
          values={data.transportInformation || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('transportInformation', key, checked)
          }
        />

        <Divider />

        <CheckboxGroup
          label="Escort"
          options={fieldOptions.escorted_to || []}
          values={data.escortedTo || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('escortedTo', key, checked)
          }
        />

        <Divider />

        <CheckboxGroup
          label="Safe Space"
          options={SAFE_SPACE_OPTIONS}
          values={data.safeSpace || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('safeSpace', key, checked)
          }
        />
      </Form>
    </>
  );
};

BasicSupportTab.propTypes = {
  data: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.object.isRequired,
};

export default BasicSupportTab;
