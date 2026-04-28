import React from 'react';
import PropTypes from 'prop-types';
import { Form } from 'semantic-ui-react';

// Coerce both sides to a comparable scalar so type drift between the
// schema (e.g. int 0) and a stringified value (from the wire, a URL param,
// or an AI response that returns "0") doesn't silently leave radios unselected.
// Booleans stay distinct from "true"/"false"; everything else compares by string.
const isSameValue = (a, b) => {
    if (a === b) return true;
    if (a === null || a === undefined || b === null || b === undefined) return false;
    if (typeof a === 'boolean' || typeof b === 'boolean') return a === b;
    return String(a) === String(b);
};

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
                        checked={isSameValue(value, opt.value)}
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
