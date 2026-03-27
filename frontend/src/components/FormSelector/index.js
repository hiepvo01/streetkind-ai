import React from 'react';
import { Container, Grid, Header, Button, Form, Select } from 'semantic-ui-react';
import PropTypes from 'prop-types';

const FormSelector = ({
    appName,
    appSubtitle,
    formTypes,
    activeFormType,
    onSelectFormType,
    sites,
    activeSite,
    onSelectSite,
}) => {
    const siteOptions = sites.map((s) => ({
        key: s.key,
        value: s.key,
        text: s.label,
    }));

    return (
        <Container style={{ paddingTop: '2rem' }}>
            <Grid container>
                <Grid.Row>
                    <Header as='h1' className='sectionHeader'>
                        {appName}
                        <Header.Subheader>{appSubtitle}</Header.Subheader>
                    </Header>
                </Grid.Row>
                <Grid.Row>
                    <Grid.Column mobile={16} tablet={8} computer={8}>
                        <Button.Group fluid size='large'>
                            {formTypes.map((ft) => (
                                <Button
                                    key={ft.key}
                                    color={activeFormType === ft.key ? 'blue' : undefined}
                                    active={activeFormType === ft.key}
                                    onClick={() => onSelectFormType(ft.key)}
                                    icon={ft.icon}
                                    content={ft.label}
                                />
                            ))}
                        </Button.Group>
                    </Grid.Column>
                    <Grid.Column mobile={16} tablet={8} computer={8}>
                        <Form>
                            <Form.Field
                                control={Select}
                                label='Site'
                                options={siteOptions}
                                value={activeSite}
                                onChange={(e, { value }) => onSelectSite(value)}
                                placeholder='Select site'
                            />
                        </Form>
                    </Grid.Column>
                </Grid.Row>
            </Grid>
        </Container>
    );
};

FormSelector.propTypes = {
    appName: PropTypes.string.isRequired,
    appSubtitle: PropTypes.string.isRequired,
    formTypes: PropTypes.array.isRequired,
    activeFormType: PropTypes.string,
    onSelectFormType: PropTypes.func.isRequired,
    sites: PropTypes.array.isRequired,
    activeSite: PropTypes.string,
    onSelectSite: PropTypes.func.isRequired,
};

export default FormSelector;
