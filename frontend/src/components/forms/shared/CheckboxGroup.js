import React from 'react';
import PropTypes from 'prop-types';
import { Checkbox, Form, Label } from 'semantic-ui-react';

const CheckboxGroup = ({ label, options, values, onChange, required, error }) => {
    return (
        <Form.Field error={!!error}>
            {label && (
                <label style={{ fontWeight: 'bold' }}>
                    {label}
                    {required && <span style={{ color: '#db2828' }}> *</span>}
                </label>
            )}
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
            {error && (
                <Label pointing color="red" style={{ marginTop: '0.4em' }}>
                    {error}
                </Label>
            )}
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
    required: PropTypes.bool,
    error: PropTypes.string,
};

CheckboxGroup.defaultProps = {
    label: '',
    values: {},
    required: false,
    error: '',
};

export default CheckboxGroup;
