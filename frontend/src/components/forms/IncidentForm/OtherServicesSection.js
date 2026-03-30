import React from 'react';
import PropTypes from 'prop-types';
import { Form } from 'semantic-ui-react';
import CheckboxGroup from '../shared/CheckboxGroup';

/**
 * "Other Services Involved" section.
 * Renders boolean checkboxes driven by config options, plus a free-text "Others" field.
 */
const OtherServicesSection = ({ data, onChange, options }) => {
  const handleCheckboxChange = (key, checked) => {
    onChange({ ...data, [key]: checked });
  };

  const handleOthersChange = (e, { value }) => {
    onChange({ ...data, others: value });
  };

  return (
    <>
      <CheckboxGroup
        label=""
        options={options}
        values={data}
        onChange={handleCheckboxChange}
      />
      <Form.Input
        label="Others"
        placeholder="Others (please specify)"
        value={data.others || ''}
        onChange={handleOthersChange}
      />
    </>
  );
};

OtherServicesSection.propTypes = {
  data: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
    })
  ).isRequired,
};

export default OtherServicesSection;
