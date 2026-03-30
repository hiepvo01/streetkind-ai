import React from 'react';
import PropTypes from 'prop-types';
import { Form } from 'semantic-ui-react';

/**
 * A group of Semantic UI radio buttons driven by a config array.
 * Matches the SKSSIR SemanticReduxFormRadioGroup pattern (grouped/vertical).
 */
const RadioGroup = ({ label, options, value, onChange }) => {
  return (
    <Form.Field>
      <Form.Field>
        <label style={{ fontWeight: 'bold' }}>{label}</label>
      </Form.Field>
      <Form.Group grouped>
        {options.map((option) => (
          <Form.Radio
            key={option.value}
            label={option.label}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
        ))}
      </Form.Group>
    </Form.Field>
  );
};

RadioGroup.propTypes = {
  label: PropTypes.string.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      label: PropTypes.string.isRequired,
    })
  ).isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onChange: PropTypes.func.isRequired,
};

RadioGroup.defaultProps = {
  value: null,
};

export default RadioGroup;
