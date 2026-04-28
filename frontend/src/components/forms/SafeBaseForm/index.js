import React from 'react';
import PropTypes from 'prop-types';
import { Divider, Header, Label, Segment } from 'semantic-ui-react';
import PeopleCountSection from './PeopleCountSection';
import AssistanceSection from './AssistanceSection';

const formatStartTime = (ms) => {
  if (ms == null || Number.isNaN(Number(ms))) return null;
  return new Date(Number(ms)).toLocaleString('en-AU', {
    dateStyle: 'short',
    timeStyle: 'short',
  });
};

const SafeBaseForm = ({ data, onChange, fieldOptions }) => {
  // GET /api/config returns field_options.safebase as a merged object (e.g. assistance_rendered: [...]).
  // AssistanceSection expects an array and calls .map() on it — pass that array, not the whole object.
  const assistanceFieldOptions = Array.isArray(fieldOptions)
    ? fieldOptions
    : fieldOptions?.assistance_rendered ?? [];

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

  const timeLabel = formatStartTime(data.startTime);

  return (
    <div>
      {(data.site || timeLabel) && (
        <Segment secondary>
          <Header as='h4'>
            {data.site && (
              <>
                Site: <Label>{data.site}</Label>
              </>
            )}
            {data.site && timeLabel && ' · '}
            {timeLabel && (
              <>
                Time: <Label>{timeLabel}</Label>
              </>
            )}
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
        fieldOptions={assistanceFieldOptions}
      />
    </div>
  );
};

SafeBaseForm.propTypes = {
  data: PropTypes.shape({
    site: PropTypes.string,
    startTime: PropTypes.number,
    male: PropTypes.object,
    female: PropTypes.object,
    nonBinary: PropTypes.object,
    assistanceRendered: PropTypes.object,
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.oneOfType([
    PropTypes.arrayOf(
      PropTypes.shape({
        key: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired,
        icon: PropTypes.string,
      })
    ),
    PropTypes.object,
  ]).isRequired,
};

export default SafeBaseForm;
