import React from 'react';
import PropTypes from 'prop-types';
import { Checkbox, Form } from 'semantic-ui-react';

const CheckboxGroup = ({ label, options, values, onChange }) => {
    return (
        <Form.Field>
            {label && <label style={{ fontWeight: 'bold' }}>{label}</label>}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6em 1.2em', paddingTop: '0.3em' }}>
                {options.map((opt) => (
                    <Checkbox
                        key={opt.key}
                        label={opt.label}
                        checked={!!(values && values[opt.key])}
                        onChange={(e, { checked }) => onChange(opt.key, checked)}
                        style={{ minWidth: 'fit-content' }}
                    />
                ))}
            </div>
        </Form.Field>
    );
};

CheckboxGroup.propTypes = {
    label: PropTypes.string,
    options: PropTypes.arrayOf(
        PropTypes.shape({
            key: PropTypes.string.isRequired,
            label: PropTypes.string.isRequired,
        })
    ).isRequired,
    values: PropTypes.object,
    onChange: PropTypes.func.isRequired,
};

CheckboxGroup.defaultProps = {
    label: '',
    values: {},
};

export default CheckboxGroup;
