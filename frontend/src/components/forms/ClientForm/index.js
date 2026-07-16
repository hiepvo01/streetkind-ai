import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { Icon, Menu, Segment } from 'semantic-ui-react';
import ClientInfoTab from './ClientInfoTab';
import BasicSupportTab from './BasicSupportTab';
import HealthSupportTab from './HealthSupportTab';
import RiskMinimizationTab from './RiskMinimizationTab';
import ServicesReferredTab from './ServicesReferredTab';

const TABS = [
  { key: 'clientInfo', label: 'Client Info', Component: ClientInfoTab },
  { key: 'basicSupport', label: 'Basic Support', Component: BasicSupportTab },
  { key: 'healthSupport', label: 'Health Support', Component: HealthSupportTab },
  { key: 'riskMinimisation', label: 'Risk Minimisation', Component: RiskMinimizationTab },
  { key: 'servicesReferred', label: 'Services Referred', Component: ServicesReferredTab },
];

const ClientForm = ({ data, onChange, fieldOptions, errors, showErrors }) => {
  const [activeTab, setActiveTab] = useState('clientInfo');

  // All required client fields live on the Client Info tab. On a failed submit,
  // jump the user there so the red labels are visible (rising edge only, so
  // they can still navigate away afterwards).
  const hasErrors = Object.keys(errors).length > 0;
  const prevShowErrors = useRef(false);
  useEffect(() => {
    if (showErrors && !prevShowErrors.current && hasErrors) setActiveTab('clientInfo');
    prevShowErrors.current = showErrors;
  }, [showErrors, hasErrors]);

  const activeConfig = TABS.find((t) => t.key === activeTab);
  const ActiveComponent = activeConfig ? activeConfig.Component : null;

  return (
    <div>
      <Menu pointing secondary>
        {TABS.map((tab) => (
          <Menu.Item
            key={tab.key}
            active={activeTab === tab.key}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
            {tab.key === 'clientInfo' && showErrors && hasErrors && (
              <Icon name="exclamation circle" color="red" style={{ marginLeft: '0.4em' }} />
            )}
          </Menu.Item>
        ))}
      </Menu>
      <Segment basic>
        {ActiveComponent && (
          <ActiveComponent
            data={data}
            onChange={onChange}
            fieldOptions={fieldOptions}
            errors={errors}
            showErrors={showErrors}
          />
        )}
      </Segment>
    </div>
  );
};

ClientForm.propTypes = {
  data: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  fieldOptions: PropTypes.object.isRequired,
  errors: PropTypes.object,
  showErrors: PropTypes.bool,
};

ClientForm.defaultProps = {
  errors: {},
  showErrors: false,
};

export default ClientForm;
