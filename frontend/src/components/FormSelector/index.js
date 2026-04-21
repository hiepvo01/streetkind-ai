import React from 'react';
import { Container, Header, Button, Form, Select, Segment } from 'semantic-ui-react';
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

    const controlsWidth = { maxWidth: '920px', width: '100%', marginLeft: 'auto', marginRight: 'auto' };

    return (
        <Container style={{ paddingTop: '2rem' }}>
            <div style={controlsWidth}>
                <Header as='h1' className='sectionHeader' textAlign='center'>
                    {appName}
                    <Header.Subheader>{appSubtitle}</Header.Subheader>
                </Header>

                <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                    <Button.Group fluid size='huge'>
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
                </div>

                <div
                    style={{
                        marginTop: '1.35rem',
                        display: 'flex',
                        justifyContent: 'center',
                    }}
                >
                    <Segment
                        secondary
                        padded
                        style={{
                            margin: 0,
                            width: '100%',
                            maxWidth: 'min(100%, 28rem)',
                            textAlign: 'left',
                            borderRadius: '0.28571429rem',
                        }}
                    >
                        <Form size='large'>
                            <Form.Field style={{ marginBottom: 0 }}>
                                <label>Site</label>
                                <Select
                                    selection
                                    fluid
                                    options={siteOptions}
                                    value={activeSite}
                                    onChange={(e, { value }) => onSelectSite(value)}
                                    placeholder='Choose site…'
                                    aria-label='Site: open list to choose a location'
                                />
                            </Form.Field>
                        </Form>
                    </Segment>
                </div>
            </div>
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
