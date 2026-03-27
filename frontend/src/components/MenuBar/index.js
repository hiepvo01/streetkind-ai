import React from 'react';
import { Menu, Icon, Image } from 'semantic-ui-react';
import PropTypes from 'prop-types';

import streetKindLogo from '../../assets/street-kind-logo-black.svg';

const MenuBar = ({ appName, onToggleSidebar }) => {
    return (
        <Menu size='huge' attached='top'>
            <Menu.Item onClick={onToggleSidebar}>
                <Icon name='sidebar' />
            </Menu.Item>
            <Menu.Item style={{ margin: '0 auto' }}>
                <Image
                    src={streetKindLogo}
                    size='tiny'
                    centered
                    style={{ marginTop: 8 }}
                />
            </Menu.Item>
            <Menu.Item position='right'>
                <Icon name='microphone' color='blue' />
                {appName}
            </Menu.Item>
        </Menu>
    );
};

MenuBar.propTypes = {
    appName: PropTypes.string.isRequired,
    onToggleSidebar: PropTypes.func.isRequired,
};

export default MenuBar;
