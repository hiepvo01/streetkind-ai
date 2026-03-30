import React from 'react';
import PropTypes from 'prop-types';
import { Form } from 'semantic-ui-react';
import CheckboxGroup from '../shared/CheckboxGroup';

/**
 * "Incident Referred By" section.
 * Renders boolean checkboxes driven by config options, plus a free-text "Other" field.
 */
const EncounteredBySection = ({ data, onChange, options }) => {
  const handleCheckboxChange = (key, checked) => {
    onChange({ ...data, [key]: checked });
  };

  const handleOtherChange = (e, { value }) => {
    onChange({ ...data, other: value });
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
        label="Other"
        placeholder="Other (please specify)"
        value={data.other || ''}
        onChange={handleOtherChange}
      />
    </>
  );
};

EncounteredBySection.propTypes = {
  data: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
    })
  ).isRequired,
};

export default EncounteredBySection;
