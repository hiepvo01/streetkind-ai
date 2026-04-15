import React from 'react';
import { Menu, Sidebar, Icon } from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { useAuth } from '../../context/AuthContext';

const NavSidebar = ({
    visible, onToggle, formTypes, activeFormType,
    onSelectFormType, currentView, onShowDashboard, onShowMonitor,
}) => {
    const { profile, logout } = useAuth();

    return (
        <Sidebar
            as={Menu}
            animation='push'
            width='thin'
            visible={visible}
            icon='labeled'
            vertical
            inverted
        >
            {profile?.firstName && (
                <Menu.Item header>
                    <Icon name='user circle' />
                    {profile.firstName}
                </Menu.Item>
            )}
            <Menu.Item
                name='dashboard'
                active={currentView === 'dashboard'}
                onClick={() => { onToggle(); onShowDashboard(); }}
            >
                <Icon name='home' />
                Dashboard
            </Menu.Item>
            {formTypes.map((ft) => (
                <Menu.Item
                    key={ft.key}
                    name={ft.key}
                    active={currentView === 'forms' && activeFormType === ft.key}
                    onClick={() => { onToggle(); onSelectFormType(ft.key); }}
                >
                    <Icon name={ft.icon} />
                    {ft.label}
                </Menu.Item>
            ))}
            <Menu.Item
                name='monitor'
                active={currentView === 'monitor'}
                onClick={() => { onToggle(); onShowMonitor(); }}
            >
                <Icon name='sitemap' />
                Monitor
            </Menu.Item>
            <Menu.Item name='about' onClick={onToggle}>
                <Icon name='info' />
                About
            </Menu.Item>
            <Menu.Item name='logout' onClick={() => { logout(); onToggle(); }}>
                <Icon name='sign out' />
                Log out
            </Menu.Item>
        </Sidebar>
    );
};

NavSidebar.propTypes = {
    visible: PropTypes.bool.isRequired,
    onToggle: PropTypes.func.isRequired,
    formTypes: PropTypes.array.isRequired,
    activeFormType: PropTypes.string,
    onSelectFormType: PropTypes.func.isRequired,
    currentView: PropTypes.string.isRequired,
    onShowDashboard: PropTypes.func.isRequired,
    onShowMonitor: PropTypes.func.isRequired,
};

export default NavSidebar;
