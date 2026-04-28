import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Button, Header, Icon, Label, Menu, Message, Modal, Segment, Table } from 'semantic-ui-react';

const formatDate = (timestamp) => {
    if (!timestamp) return '—';
    return new Date(timestamp).toLocaleDateString('en-AU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    });
};

const formatStartTime = (timestamp) => {
    if (!timestamp) return '—';
    return new Date(timestamp).toLocaleString('en-AU', {
        dateStyle: 'short',
        timeStyle: 'short',
    });
};

const truncate = (text, maxLen = 80) => {
    if (!text) return '—';
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
};

const FormList = ({ incidents, safebaseForms, formatSite, onEditIncident, onDeleteIncident }) => {
    const displaySite = (siteKey) => formatSite ? formatSite(siteKey) : (siteKey || '—');
    const hasData = incidents.length > 0 || safebaseForms.length > 0;
    const [activeTab, setActiveTab] = useState(() => (incidents.length > 0 ? 'incident' : 'safebase'));
    const [deleteTarget, setDeleteTarget] = useState(null);

    useEffect(() => {
        if (incidents.length > 0 && safebaseForms.length === 0) {
            setActiveTab('incident');
        } else if (safebaseForms.length > 0 && incidents.length === 0) {
            setActiveTab('safebase');
        }
    }, [incidents.length, safebaseForms.length]);

    if (!hasData) {
        return (
            <Message info>
                <Icon name='info circle' />
                No forms found for this user.
            </Message>
        );
    }

    const handleDelete = (inc) => {
        setDeleteTarget(inc);
    };

    const handleCancelDelete = () => setDeleteTarget(null);

    const handleConfirmDelete = () => {
        if (!deleteTarget) return;
        onDeleteIncident(deleteTarget.id);
        setDeleteTarget(null);
    };

    const incidentTable = (
        <div style={{ overflowX: 'auto' }}>
            <Table compact striped>
                <Table.Header>
                    <Table.Row>
                        <Table.HeaderCell>Date</Table.HeaderCell>
                        <Table.HeaderCell>Site</Table.HeaderCell>
                        <Table.HeaderCell>Description</Table.HeaderCell>
                        <Table.HeaderCell>Status</Table.HeaderCell>
                        <Table.HeaderCell>Actions</Table.HeaderCell>
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
                                        color={inc.status === 'completed' ? 'green' : inc.status === 'draft' ? 'yellow' : 'grey'}
                                    >
                                        {inc.status || 'unknown'}
                                    </Label>
                                </Table.Cell>
                                <Table.Cell>
                                    <Button
                                        icon='edit'
                                        size='mini'
                                        color='blue'
                                        title='Edit'
                                        onClick={() => onEditIncident(inc.id)}
                                    />
                                    <Button
                                        icon='trash'
                                        size='mini'
                                        color='red'
                                        title='Delete'
                                        onClick={() => handleDelete(inc)}
                                    />
                                </Table.Cell>
                            </Table.Row>
                        ))}
                </Table.Body>
            </Table>
        </div>
    );

    const safebaseTable = (
        <div style={{ overflowX: 'auto' }}>
            <Table compact striped>
                <Table.Header>
                    <Table.Row>
                        <Table.HeaderCell>Date</Table.HeaderCell>
                        <Table.HeaderCell>Start time</Table.HeaderCell>
                        <Table.HeaderCell>Site</Table.HeaderCell>
                    </Table.Row>
                </Table.Header>
                <Table.Body>
                    {safebaseForms
                        .sort((a, b) => (b.createdDate || 0) - (a.createdDate || 0))
                        .map((form) => (
                            <Table.Row key={form.id}>
                                <Table.Cell>{formatDate(form.createdDate)}</Table.Cell>
                                <Table.Cell>{formatStartTime(form.startTime)}</Table.Cell>
                                <Table.Cell>{displaySite(form.site)}</Table.Cell>
                            </Table.Row>
                        ))}
                </Table.Body>
            </Table>
        </div>
    );

    return (
        <div>
            <Menu tabular attached='top'>
                <Menu.Item
                    name='incident'
                    active={activeTab === 'incident'}
                    onClick={() => setActiveTab('incident')}
                >
                    Incident ({incidents.length})
                </Menu.Item>
                <Menu.Item
                    name='safebase'
                    active={activeTab === 'safebase'}
                    onClick={() => setActiveTab('safebase')}
                >
                    Safebase ({safebaseForms.length})
                </Menu.Item>
            </Menu>

            <Segment attached='bottom'>
                {activeTab === 'incident' && (
                    incidents.length === 0 ? (
                        <Message info>
                            <Icon name='info circle' />
                            No incident reports for this user.
                        </Message>
                    ) : (
                        incidentTable
                    )
                )}
                {activeTab === 'safebase' && (
                    safebaseForms.length === 0 ? (
                        <Message info>
                            <Icon name='info circle' />
                            No SafeBase forms for this user.
                        </Message>
                    ) : (
                        safebaseTable
                    )
                )}
            </Segment>

            <Modal
                size='small'
                open={!!deleteTarget}
                onClose={handleCancelDelete}
                closeIcon
            >
                <Modal.Header>
                    <Icon name='trash' />
                    Delete incident?
                </Modal.Header>
                <Modal.Content>
                    <p>
                        Delete incident from <strong>{formatDate(deleteTarget?.createdDate)}</strong>? This cannot be undone.
                    </p>
                </Modal.Content>
                <Modal.Actions>
                    <Button onClick={handleCancelDelete} content='Cancel' />
                    <Button
                        color='red'
                        icon='trash'
                        labelPosition='left'
                        content='Delete'
                        onClick={handleConfirmDelete}
                    />
                </Modal.Actions>
            </Modal>
        </div>
    );
};

FormList.propTypes = {
    incidents: PropTypes.array.isRequired,
    safebaseForms: PropTypes.array.isRequired,
    formatSite: PropTypes.func,
    onEditIncident: PropTypes.func.isRequired,
    onDeleteIncident: PropTypes.func.isRequired,
};

export default FormList;
