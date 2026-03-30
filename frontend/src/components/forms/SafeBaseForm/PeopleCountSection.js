import React from 'react';
import PropTypes from 'prop-types';
import { Grid, Header, Icon, Segment } from 'semantic-ui-react';
import NumberInput from '../shared/NumberInput';

const AGE_GROUPS = [
  { key: 'lessThan18', label: 'Less Than 18' },
  { key: 'from18to25', label: '18 to 25' },
  { key: 'from26to39', label: '26 to 39' },
  { key: 'over40', label: 'Over 40' },
];

const GENDER_SECTIONS = [
  { key: 'male', label: 'Male', icon: 'mars', color: 'blue', segmentColor: 'blue' },
  { key: 'female', label: 'Female', icon: 'venus', color: 'pink', segmentColor: 'pink' },
  { key: 'nonBinary', label: 'Non-Binary', icon: 'genderless', color: 'violet', segmentColor: 'purple' },
];

const PeopleCountSection = ({ data, onChange }) => {
  return (
    <div>
      <Header as='h2'>Number of People Entering</Header>

      {GENDER_SECTIONS.map(({ key, label, icon, color, segmentColor }) => (
        <Segment key={key} color={segmentColor}>
          <Header as='h3'>
            <Icon name={icon} color={color} />
            {label}
          </Header>
          <Grid divided stackable>
            <Grid.Row>
              {AGE_GROUPS.map(({ key: ageKey, label: ageLabel }) => (
                <NumberInput
                  key={ageKey}
                  label={ageLabel}
                  value={(data[key] && data[key][ageKey]) || 0}
                  onChange={(newValue) => onChange(key, ageKey, newValue)}
                />
              ))}
            </Grid.Row>
          </Grid>
        </Segment>
      ))}
    </div>
  );
};

PeopleCountSection.propTypes = {
  data: PropTypes.shape({
    male: PropTypes.shape({
      lessThan18: PropTypes.number,
      from18to25: PropTypes.number,
      from26to39: PropTypes.number,
      over40: PropTypes.number,
    }),
    female: PropTypes.shape({
      lessThan18: PropTypes.number,
      from18to25: PropTypes.number,
      from26to39: PropTypes.number,
      over40: PropTypes.number,
    }),
    nonBinary: PropTypes.shape({
      lessThan18: PropTypes.number,
      from18to25: PropTypes.number,
      from26to39: PropTypes.number,
      over40: PropTypes.number,
    }),
  }).isRequired,
  onChange: PropTypes.func.isRequired,
};

export default PeopleCountSection;
