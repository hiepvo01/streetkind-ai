import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    Breadcrumb,
    Button,
    Container,
    Divider,
    Grid,
    Header,
    Icon,
    Label,
    Loader,
    Message,
    Modal,
    Segment,
} from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { useAuth } from '../../context/AuthContext';
import { fetchTeam, fetchMonitorForms, fetchIncidentFull, updateIncident, deleteIncident } from '../../services/api';
import MemberCard from './MemberCard';
import FormList from './FormList';
import IncidentForm from '../forms/IncidentForm';

const ROLE_LABELS = {
    administrator: 'Administrator',
    teamLeader: 'Team Leader',
    teamMember: 'Team Member',
};

const Monitor = ({ sites = [], fieldOptions = {} }) => {
    const { user, profile } = useAuth();

    const siteMap = useMemo(() => {
        const map = {};
        sites.forEach((s) => { map[s.key] = s.label; });
        return map;
    }, [sites]);

    const formatSite = (siteKey) => siteMap[siteKey] || siteKey;

    const [breadcrumb, setBreadcrumb] = useState([]);
    const [teamData, setTeamData] = useState(null);
    const [formsData, setFormsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Edit modal state
    const [editModalOpen, setEditModalOpen] = useState(false);
    const [editFormId, setEditFormId] = useState(null);
    const [editFormData, setEditFormData] = useState(null);
    const [editLoading, setEditLoading] = useState(false);
    const [editError, setEditError] = useState(null);
    const [saving, setSaving] = useState(false);

    const currentUid = breadcrumb.length > 0
        ? breadcrumb[breadcrumb.length - 1].uid
        : user?.uid;

    const loadData = useCallback(async (uid) => {
        setLoading(true);
        setError(null);
        try {
            const [team, forms] = await Promise.all([
                fetchTeam(uid),
                fetchMonitorForms(uid),
            ]);
            setTeamData(team);
            setFormsData(forms);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (currentUid) {
            loadData(currentUid);
        }
    }, [currentUid, loadData]);

    const handleCardClick = (member) => {
        setBreadcrumb((prev) => [
            ...prev,
            {
                uid: member.uid,
                name: [member.firstName, member.lastName].filter(Boolean).join(' '),
                userLevel: member.userLevel,
            },
        ]);
    };

    const handleBreadcrumbClick = (index) => {
        if (index === -1) {
            setBreadcrumb([]);
        } else {
            setBreadcrumb((prev) => prev.slice(0, index + 1));
        }
    };

    // ── Edit / Delete handlers ───────────────────────────────────────

    const handleEditIncident = async (formId) => {
        setEditFormId(formId);
        setEditModalOpen(true);
        setEditLoading(true);
        setEditError(null);
        setEditFormData(null);
        try {
            const data = await fetchIncidentFull(formId);
            setEditFormData(data);
        } catch (e) {
            setEditError(e.message);
        } finally {
            setEditLoading(false);
        }
    };

    const handleSaveEdit = async (status) => {
        if (!editFormData || !editFormId) return;
        setSaving(true);
        setEditError(null);
        try {
            await updateIncident(editFormId, editFormData, status);
            setEditModalOpen(false);
            setEditFormId(null);
            setEditFormData(null);
            if (currentUid) loadData(currentUid);
        } catch (e) {
            setEditError(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteIncident = async (formId) => {
        try {
            await deleteIncident(formId);
            if (currentUid) loadData(currentUid);
        } catch (e) {
            setError('Delete failed: ' + e.message);
        }
    };

    const handleCloseModal = () => {
        setEditModalOpen(false);
        setEditFormId(null);
        setEditFormData(null);
        setEditError(null);
    };

    const viewedUser = teamData?.user;
    const isOwnPage = breadcrumb.length === 0;

    const incidentFieldOptions = {
        ...(fieldOptions.incident || {}),
        ...(fieldOptions.client || {}),
    };

    return (
        <Container style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
            {/* Breadcrumb navigation */}
            <Breadcrumb size='large'>
                <Breadcrumb.Section
                    link={breadcrumb.length > 0}
                    active={breadcrumb.length === 0}
                    onClick={() => handleBreadcrumbClick(-1)}
                >
                    <Icon name='home' />
                    My Monitor
                </Breadcrumb.Section>
                {breadcrumb.map((crumb, i) => (
                    <React.Fragment key={crumb.uid}>
                        <Breadcrumb.Divider icon='right chevron' />
                        <Breadcrumb.Section
                            link={i < breadcrumb.length - 1}
                            active={i === breadcrumb.length - 1}
                            onClick={() => handleBreadcrumbClick(i)}
                        >
                            {crumb.name}
                        </Breadcrumb.Section>
                    </React.Fragment>
                ))}
            </Breadcrumb>

            <Divider />

            {/* Loading / error states */}
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

            {!loading && !error && viewedUser && (
                <>
                    {/* User header */}
                    <Segment secondary>
                        <Header as='h2'>
                            <Icon name='user circle' />
                            <Header.Content>
                                {isOwnPage ? (
                                    <>
                                        {profile?.firstName} {profile?.lastName}
                                    </>
                                ) : (
                                    <>
                                        {viewedUser.firstName} {viewedUser.lastName}
                                    </>
                                )}
                                <Header.Subheader>
                                    <Label color='blue' size='small' style={{ marginTop: '0.4em' }}>
                                        {ROLE_LABELS[viewedUser.userLevel] || viewedUser.userLevel}
                                    </Label>
                                    {viewedUser.site && (
                                        <Label size='small' style={{ marginTop: '0.4em' }}>
                                            <Icon name='map marker alternate' />
                                            {formatSite(viewedUser.site)}
                                        </Label>
                                    )}
                                </Header.Subheader>
                            </Header.Content>
                        </Header>
                    </Segment>

                    {/* Team Leaders section (admins only) */}
                    {viewedUser.userLevel === 'administrator' && (
                        <>
                            <Header as='h3'>
                                <Icon name='users' />
                                Team Leaders
                            </Header>
                            {teamData.teamLeaders?.length > 0 ? (
                                <Grid stackable>
                                    {teamData.teamLeaders.map((tl) => (
                                        <MemberCard
                                            key={tl.uid}
                                            member={tl}
                                            onClick={handleCardClick}
                                            formatSite={formatSite}
                                        />
                                    ))}
                                </Grid>
                            ) : (
                                <Message info>
                                    <Icon name='info circle' />
                                    No team leaders assigned yet.
                                </Message>
                            )}
                            <Divider />
                        </>
                    )}

                    {/* Team Members section (admins and team leaders) */}
                    {(viewedUser.userLevel === 'administrator' || viewedUser.userLevel === 'teamLeader') && (
                        <>
                            <Header as='h3'>
                                <Icon name='user' />
                                Team Members
                            </Header>
                            {teamData.teamMembers?.length > 0 ? (
                                <Grid stackable>
                                    {teamData.teamMembers.map((tm) => (
                                        <MemberCard
                                            key={tm.uid}
                                            member={tm}
                                            onClick={handleCardClick}
                                            formatSite={formatSite}
                                        />
                                    ))}
                                </Grid>
                            ) : (
                                <Message info>
                                    <Icon name='info circle' />
                                    No team members assigned yet.
                                </Message>
                            )}
                            <Divider />
                        </>
                    )}

                    {/* Forms section */}
                    <Header as='h3'>
                        <Icon name='clipboard list' />
                        {isOwnPage ? 'Your Forms' : `${viewedUser.firstName}'s Forms`}
                    </Header>
                    {formsData && (
                        <FormList
                            incidents={formsData.incidents || []}
                            safebaseForms={formsData.safebaseForms || []}
                            formatSite={formatSite}
                            onEditIncident={handleEditIncident}
                            onDeleteIncident={handleDeleteIncident}
                        />
                    )}
                </>
            )}

            {/* Edit Incident Modal */}
            <Modal
                open={editModalOpen}
                onClose={handleCloseModal}
                size='large'
                closeIcon
            >
                <Modal.Header>
                    <Icon name='edit' />
                    Edit Incident Report
                </Modal.Header>
                <Modal.Content scrolling>
                    {editLoading && (
                        <Segment basic>
                            <Loader active inline='centered' content='Loading incident...' />
                        </Segment>
                    )}
                    {editError && (
                        <Message error>
                            <Icon name='warning circle' />
                            {editError}
                        </Message>
                    )}
                    {editFormData && !editLoading && (
                        <IncidentForm
                            data={editFormData}
                            onChange={setEditFormData}
                            fieldOptions={incidentFieldOptions}
                            sites={sites}
                        />
                    )}
                </Modal.Content>
                <Modal.Actions>
                    <Button
                        color='green'
                        onClick={() => handleSaveEdit('completed')}
                        disabled={saving || editLoading || !editFormData}
                        loading={saving}
                        icon='check'
                        labelPosition='left'
                        content='Save as Completed'
                    />
                    <Button
                        color='yellow'
                        onClick={() => handleSaveEdit('draft')}
                        disabled={saving || editLoading || !editFormData}
                        loading={saving}
                        icon='save outline'
                        labelPosition='left'
                        content='Save as Draft'
                    />
                    <Button
                        onClick={handleCloseModal}
                        disabled={saving}
                        content='Cancel'
                    />
                </Modal.Actions>
            </Modal>
        </Container>
    );
};

Monitor.propTypes = {
    sites: PropTypes.array,
    fieldOptions: PropTypes.object,
};

export default Monitor;
