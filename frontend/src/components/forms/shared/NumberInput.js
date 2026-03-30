import React from 'react';
import PropTypes from 'prop-types';
import { Button, Grid, Icon, Segment, Statistic } from 'semantic-ui-react';

const NumberInput = ({ label, value, onChange, min, icon, color }) => {
    const handleDecrement = () => {
        if (value > min) onChange(value - 1);
    };
    const handleIncrement = () => {
        onChange(value + 1);
    };

    return (
        <Grid.Column mobile={8} tablet={4} computer={4} textAlign="center">
            <Segment basic compact style={{ margin: '0 auto', padding: '0.5em' }}>
                {icon && <Icon name={icon} color={color} size="small" />}
                <Statistic size="mini">
                    <Statistic.Value>{value}</Statistic.Value>
                    <Statistic.Label style={{ fontSize: '0.8em' }}>{label}</Statistic.Label>
                </Statistic>
                <div style={{ marginTop: '0.3em' }}>
                    <Button.Group size="mini">
                        <Button icon="minus" color="red" onClick={handleDecrement} disabled={value <= min} type="button" />
                        <Button icon="plus" color="green" onClick={handleIncrement} type="button" />
                    </Button.Group>
                </div>
            </Segment>
        </Grid.Column>
    );
};

NumberInput.propTypes = {
    label: PropTypes.string.isRequired,
    value: PropTypes.number.isRequired,
    onChange: PropTypes.func.isRequired,
    min: PropTypes.number,
    icon: PropTypes.string,
    color: PropTypes.string,
};

NumberInput.defaultProps = {
    min: 0,
    icon: null,
    color: null,
};

export default NumberInput;
