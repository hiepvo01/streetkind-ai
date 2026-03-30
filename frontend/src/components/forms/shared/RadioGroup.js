import React from 'react';
import PropTypes from 'prop-types';
import { Form } from 'semantic-ui-react';

const RadioGroup = ({ label, options, value, onChange }) => {
    return (
        <Form.Field>
            {label && <label style={{ fontWeight: 'bold' }}>{label}</label>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4em', paddingTop: '0.3em' }}>
                {options.map((opt) => (
                    <Form.Radio
                        key={String(opt.value)}
                        label={opt.label}
                        value={opt.value}
                        checked={value === opt.value}
                        onChange={() => onChange(opt.value)}
                    />
                ))}
            </div>
        </Form.Field>
    );
};

RadioGroup.propTypes = {
    label: PropTypes.string,
    options: PropTypes.arrayOf(
        PropTypes.shape({
            value: PropTypes.any.isRequired,
            label: PropTypes.string.isRequired,
        })
    ).isRequired,
    value: PropTypes.any,
    onChange: PropTypes.func.isRequired,
};

RadioGroup.defaultProps = {
    label: '',
    value: null,
};

export default RadioGroup;
