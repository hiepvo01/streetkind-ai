import React from 'react';
import PropTypes from 'prop-types';
import { Divider, Header, Label, Segment } from 'semantic-ui-react';
import PeopleCountSection from './PeopleCountSection';
import AssistanceSection from './AssistanceSection';

const SafeBaseForm = ({ data, onChange, fieldOptions }) => {
  const handlePeopleCountChange = (gender, ageGroup, value) => {
    onChange({
      ...data,
      [gender]: {
        ...data[gender],
        [ageGroup]: value,
      },
    });
  };

  const handleAssistanceChange = (key, value) => {
    onChange({
      ...data,
      assistanceRendered: {
        ...data.assistanceRendered,
        [key]: value,
      },
    });
  };

  return (
    <div>
      {data.site && (
        <Segment secondary>
          <Header as='h4'>
            Site: <Label>{data.site}</Label>
          </Header>
        </Segment>
      )}

      <PeopleCountSection
        data={{
          male: data.male || {},
          female: data.female || {},
          nonBinary: data.nonBinary || {},
        }}
        onChange={handlePeopleCountChange}
      />

      <Divider />

      <AssistanceSection
        data={data.assistanceRendered || {}}
        onChange={handleAssistanceChange}
        fieldOptions={fieldOptions}
      />
    </div>
  );
};

SafeBaseForm.propTypes = {
  data: PropTypes.shape({
    site: PropTypes.string,
    male: PropTypes.object,
    female: PropTypes.object,
    nonBinary: PropTypes.object,
    assistanceRendered: PropTypes.object,
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

export default SafeBaseForm;
