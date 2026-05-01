import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Menu, Segment } from 'semantic-ui-react';
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

const ClientForm = ({ data, onChange, fieldOptions }) => {
  const [activeTab, setActiveTab] = useState('clientInfo');

  const activeConfig = TABS.find((t) => t.key === activeTab);
  const ActiveComponent = activeConfig ? activeConfig.Component : null;

  return (
    <div>
      <Menu pointing secondary>
        {TABS.map((tab) => (
          <Menu.Item
            key={tab.key}
            name={tab.label}
            active={activeTab === tab.key}
            onClick={() => setActiveTab(tab.key)}
          />
        ))}
      </Menu>
      <Segment basic>
        {ActiveComponent && (
          <ActiveComponent
            data={data}
            onChange={onChange}
            fieldOptions={fieldOptions}
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
};

export default ClientForm;
