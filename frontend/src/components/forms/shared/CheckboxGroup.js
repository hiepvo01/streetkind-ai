import React from 'react';
import PropTypes from 'prop-types';
import { Checkbox, Form } from 'semantic-ui-react';

/**
 * A group of Semantic UI checkboxes driven by a config array.
 * Matches the SKSSIR NewSemanticReduxFormCheckbox pattern.
 */
const CheckboxGroup = ({ label, options, values, onChange }) => {
  return (
    <Form.Field>
      <Form.Field>
        <label style={{ fontWeight: 'bold' }}>{label}</label>
      </Form.Field>
      <Form.Group widths="equal">
        {options.map((option) => (
          <Form.Field key={option.key}>
            <Checkbox
              label={option.label}
              checked={!!values[option.key]}
              onChange={(e, data) => onChange(option.key, data.checked)}
            />
          </Form.Field>
        ))}
      </Form.Group>
    </Form.Field>
  );
};

CheckboxGroup.propTypes = {
  label: PropTypes.string.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
    })
  ).isRequired,
  values: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
};

export default CheckboxGroup;
