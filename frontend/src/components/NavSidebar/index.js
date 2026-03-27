import React from 'react';
import { Menu, Sidebar, Icon } from 'semantic-ui-react';
import PropTypes from 'prop-types';

const NavSidebar = ({ visible, onToggle, formTypes, activeFormType, onSelectFormType }) => {
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
            {formTypes.map((ft) => (
                <Menu.Item
                    key={ft.key}
                    name={ft.key}
                    active={activeFormType === ft.key}
                    onClick={() => { onToggle(); onSelectFormType(ft.key); }}
                >
                    <Icon name={ft.icon} />
                    {ft.label}
                </Menu.Item>
            ))}
            <Menu.Item name='about' onClick={onToggle}>
                <Icon name='info' />
                About
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
};

export default NavSidebar;
