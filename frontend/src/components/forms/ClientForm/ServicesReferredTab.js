import React from 'react';
import PropTypes from 'prop-types';
import { Divider, Form, Header } from 'semantic-ui-react';
import CheckboxGroup from '../shared/CheckboxGroup';

const SERVICE_INFORMATION_OPTIONS = [
  { key: 'contactedService', label: 'Contacted Service' },
  { key: 'infoProvided', label: 'Provided Service Information' },
];

const ServicesReferredTab = ({ data, onChange, fieldOptions }) => {
  const handleCheckboxChange = (section, key, checked) => {
    onChange({
      ...data,
      [section]: { ...data[section], [key]: checked },
    });
  };

  return (
    <>
      <Header as="h2">Services Referred</Header>
      <Form size="large">
        <CheckboxGroup
          label="Client Service Referrals"
          options={fieldOptions.service_referrals || []}
          values={data.clientServiceReferrals || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('clientServiceReferrals', key, checked)
          }
        />

        <Divider />

        <CheckboxGroup
          label="Service Information"
          options={SERVICE_INFORMATION_OPTIONS}
          values={data.serviceInformation || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('serviceInformation', key, checked)
          }
        />

        <Divider />

        <CheckboxGroup
          label="Other Support"
          options={fieldOptions.other_support || []}
          values={data.otherSupport || {}}
          onChange={(key, checked) =>
            handleCheckboxChange('otherSupport', key, checked)
          }
        />
      </Form>
    </>
  );
};

ServicesReferredTab.propTypes = {
  data: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.object.isRequired,
};

export default ServicesReferredTab;
