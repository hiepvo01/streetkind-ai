import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Container, Divider, Header, Icon, Loader, Message, Segment } from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { useAuth } from '../../context/AuthContext';
import { deleteIncident, fetchMonitorForms } from '../../services/api';
import FormList from '../Monitor/FormList';
import IncidentEditModal from '../Monitor/IncidentEditModal';

const MyIncidents = ({ sites = [], fieldOptions = {} }) => {
    const { user } = useAuth();

    const siteMap = useMemo(() => {
        const map = {};
        sites.forEach((s) => { map[s.key] = s.label; });
        return map;
    }, [sites]);

    const formatSite = (siteKey) => siteMap[siteKey] || siteKey;

    const [formsData, setFormsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [editModalOpen, setEditModalOpen] = useState(false);
    const [editFormId, setEditFormId] = useState(null);

    const loadForms = useCallback(async () => {
        if (!user?.uid) return;
        setLoading(true);
        setError(null);
        try {
            const forms = await fetchMonitorForms(user.uid);
            setFormsData(forms);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [user?.uid]);

    useEffect(() => {
        loadForms();
    }, [loadForms]);

    const handleEditIncident = (formId) => {
        setEditFormId(formId);
        setEditModalOpen(true);
    };

    const handleCloseModal = () => {
        setEditModalOpen(false);
        setEditFormId(null);
    };

    const handleDeleteIncident = async (formId) => {
        try {
            await deleteIncident(formId);
            loadForms();
        } catch (e) {
            setError('Delete failed: ' + e.message);
        }
    };

    const incidentFieldOptions = {
        ...(fieldOptions.incident || {}),
        ...(fieldOptions.client || {}),
    };

    return (
        <Container style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
            <Header as='h2'>
                <Icon name='clipboard list' />
                <Header.Content>
                    My Incidents
                    <Header.Subheader>
                        Your incident reports and SafeBase forms (drafts and submitted)
                    </Header.Subheader>
                </Header.Content>
            </Header>

            <Divider />

            {loading && (
                <Segment basic>
                    <Loader active inline='centered' content='Loading...' />
                </Segment>
            )}

            {error && (
                <Message error>
                    <Icon name='warning circle' />
                    {error}
                </Message>
            )}

            {!loading && !error && formsData && (
                <FormList
                    incidents={formsData.incidents || []}
                    safebaseForms={formsData.safebaseForms || []}
                    formatSite={formatSite}
                    onEditIncident={handleEditIncident}
                    onDeleteIncident={handleDeleteIncident}
                />
            )}

            <IncidentEditModal
                open={editModalOpen}
                onClose={handleCloseModal}
                formId={editFormId}
                sites={sites}
                incidentFieldOptions={incidentFieldOptions}
                onSaved={loadForms}
            />
        </Container>
    );
};

MyIncidents.propTypes = {
    sites: PropTypes.array,
    fieldOptions: PropTypes.object,
};

export default MyIncidents;
