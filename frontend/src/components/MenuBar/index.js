import React from 'react';
import { Menu, Icon, Image } from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { useAuth } from '../../context/AuthContext';

const MenuBar = ({ appName, onToggleSidebar }) => {
    const { profile } = useAuth();

    return (
        <Menu size='huge' attached='top'>
            <Menu.Item onClick={onToggleSidebar}>
                <Icon name='sidebar' />
            </Menu.Item>
            <Menu.Item style={{ margin: '0 auto' }}>
                <Image
                    src='/street-kind-logo-black.svg'
                    size='tiny'
                    centered
                    style={{ marginTop: 8 }}
                />
            </Menu.Item>
            <Menu.Item position='right'>
                <Icon name='user circle outline' color='blue' />
                {profile?.firstName || 'User'}
            </Menu.Item>
        </Menu>
    );
};

MenuBar.propTypes = {
    appName: PropTypes.string.isRequired,
    onToggleSidebar: PropTypes.func.isRequired,
};

export default MenuBar;
