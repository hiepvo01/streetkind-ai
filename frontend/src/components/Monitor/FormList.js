import React from 'react';
import PropTypes from 'prop-types';
import { Header, Icon, Label, Message, Segment, Table } from 'semantic-ui-react';

const formatDate = (timestamp) => {
    if (!timestamp) return '—';
    return new Date(timestamp).toLocaleDateString('en-AU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    });
};

const truncate = (text, maxLen = 80) => {
    if (!text) return '—';
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
};

const FormList = ({ incidents, safebaseForms, formatSite }) => {
    const displaySite = (siteKey) => formatSite ? formatSite(siteKey) : (siteKey || '—');
    const hasData = incidents.length > 0 || safebaseForms.length > 0;

    if (!hasData) {
        return (
            <Message info>
                <Icon name='info circle' />
                No forms found for this user.
            </Message>
        );
    }

    return (
        <div>
            {incidents.length > 0 && (
                <Segment>
                    <Header as='h4'>
                        <Icon name='file alternate outline' />
                        Incident Reports ({incidents.length})
                    </Header>
                    <div style={{ overflowX: 'auto' }}>
                        <Table compact striped>
                            <Table.Header>
                                <Table.Row>
                                    <Table.HeaderCell>Date</Table.HeaderCell>
                                    <Table.HeaderCell>Site</Table.HeaderCell>
                                    <Table.HeaderCell>Description</Table.HeaderCell>
                                    <Table.HeaderCell>Status</Table.HeaderCell>
                                </Table.Row>
                            </Table.Header>
                            <Table.Body>
                                {incidents
                                    .sort((a, b) => (b.createdDate || 0) - (a.createdDate || 0))
                                    .map((inc) => (
                                        <Table.Row key={inc.id}>
                                            <Table.Cell>{formatDate(inc.createdDate)}</Table.Cell>
                                            <Table.Cell>{displaySite(inc.site)}</Table.Cell>
                                            <Table.Cell>{truncate(inc.incidentDescription)}</Table.Cell>
                                            <Table.Cell>
                                                <Label
                                                    size='tiny'
                                                    color={inc.status === 'completed' ? 'green' : 'grey'}
                                                >
                                                    {inc.status || 'unknown'}
                                                </Label>
                                            </Table.Cell>
                                        </Table.Row>
                                    ))}
                            </Table.Body>
                        </Table>
                    </div>
                </Segment>
            )}

            {safebaseForms.length > 0 && (
                <Segment>
                    <Header as='h4'>
                        <Icon name='shield alternate' />
                        SafeBase Forms ({safebaseForms.length})
                    </Header>
                    <div style={{ overflowX: 'auto' }}>
                        <Table compact striped>
                            <Table.Header>
                                <Table.Row>
                                    <Table.HeaderCell>Date</Table.HeaderCell>
                                    <Table.HeaderCell>Site</Table.HeaderCell>
                                </Table.Row>
                            </Table.Header>
                            <Table.Body>
                                {safebaseForms
                                    .sort((a, b) => (b.createdDate || 0) - (a.createdDate || 0))
                                    .map((form) => (
                                        <Table.Row key={form.id}>
                                            <Table.Cell>{formatDate(form.createdDate)}</Table.Cell>
                                            <Table.Cell>{displaySite(form.site)}</Table.Cell>
                                        </Table.Row>
                                    ))}
                            </Table.Body>
                        </Table>
                    </div>
                </Segment>
            )}
        </div>
    );
};

FormList.propTypes = {
    incidents: PropTypes.array.isRequired,
    safebaseForms: PropTypes.array.isRequired,
    formatSite: PropTypes.func,
};

export default FormList;
