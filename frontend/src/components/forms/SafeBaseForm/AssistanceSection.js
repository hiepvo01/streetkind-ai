import React from 'react';
import PropTypes from 'prop-types';
import { Grid, Header } from 'semantic-ui-react';
import NumberInput from '../shared/NumberInput';

const AssistanceSection = ({ data, onChange, fieldOptions }) => {
  return (
    <div>
      <Header as='h2'>Amount of Assistance Rendered</Header>
      <Grid container stackable centered>
        <Grid.Row>
          {fieldOptions.map(({ key, label, icon }) => (
            <NumberInput
              key={key}
              label={label}
              value={(data && data[key]) || 0}
              onChange={(newValue) => onChange(key, newValue)}
              icon={icon}
              color='green'
            />
          ))}
        </Grid.Row>
      </Grid>
    </div>
  );
};

AssistanceSection.propTypes = {
  data: PropTypes.shape({
    directions: PropTypes.number,
    bus: PropTypes.number,
    train: PropTypes.number,
    taxi: PropTypes.number,
    deviceCharge: PropTypes.number,
    familyReconnect: PropTypes.number,
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      icon: PropTypes.string,
    })
  ).isRequired,
};

export default AssistanceSection;
