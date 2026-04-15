import React from 'react';
import { Container, Header, Icon } from 'semantic-ui-react';

const Monitor = () => {
    return (
        <Container style={{ paddingTop: '2rem' }}>
            <Header as='h1' className='sectionHeader'>
                <Icon name='sitemap' />
                <Header.Content>
                    Monitor
                    <Header.Subheader>Team hierarchy and form tracking</Header.Subheader>
                </Header.Content>
            </Header>
            <p>Loading monitor view...</p>
        </Container>
    );
};

export default Monitor;
