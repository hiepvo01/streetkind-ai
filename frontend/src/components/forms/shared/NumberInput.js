import React from 'react';
import PropTypes from 'prop-types';
import { Button, Grid, Icon, Segment, Statistic } from 'semantic-ui-react';

/**
 * A numeric counter with +/- buttons for SafeBase headcounts.
 * Matches the SKSSIR SemanticReduxFormNumberField pattern.
 */
const NumberInput = ({ label, value, onChange, min, icon, color }) => {
  const handleDecrement = () => {
    if (value > min) {
      onChange(value - 1);
    }
  };

  const handleIncrement = () => {
    onChange(value + 1);
  };

  return (
    <Grid.Column mobile={16} tablet={8} computer={4} textAlign="center">
      <Segment color={color || null}>
        <div style={{ marginBottom: '1em' }}>
          <div style={{ marginBottom: '0.5em' }}>
            <Statistic.Label style={{ fontWeight: 'bold', textTransform: 'uppercase' }}>
              {label}
            </Statistic.Label>
          </div>
          {icon && (
            <Icon name={icon} size="large" color={color || null} style={{ marginBottom: '0.5em' }} />
          )}
          <Statistic>
            <Statistic.Value>{value}</Statistic.Value>
          </Statistic>
        </div>
        <Button.Group fluid>
          <Button
            type="button"
            color="red"
            icon="minus"
            onClick={handleDecrement}
            disabled={value <= min}
          />
          <Button
            type="button"
            color="green"
            icon="plus"
            onClick={handleIncrement}
          />
        </Button.Group>
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
