import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    Breadcrumb,
    Container,
    Divider,
    Grid,
    Header,
    Icon,
    Label,
    Loader,
    Message,
    Segment,
} from 'semantic-ui-react';
import PropTypes from 'prop-types';

import { useAuth } from '../../context/AuthContext';
import { fetchTeam, fetchMonitorForms, deleteIncident } from '../../services/api';
import MemberCard from './MemberCard';
import FormList from './FormList';
import IncidentEditModal from './IncidentEditModal';

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

    const [editModalOpen, setEditModalOpen] = useState(false);
    const [editFormId, setEditFormId] = useState(null);

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

    const handleEditIncident = (formId) => {
        setEditFormId(formId);
        setEditModalOpen(true);
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

                    {isOwnPage && (viewedUser.userLevel === 'administrator' || viewedUser.userLevel === 'teamLeader') && (
                        <Message info>
                            <Icon name='info circle' />
                            Your own incident reports and SafeBase forms are listed under <strong>My Incidents</strong> in the sidebar.
                        </Message>
                    )}

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

                    {/* Forms: only when viewing a subordinate (use My Incidents for your own) */}
                    {!isOwnPage && (
                        <>
                            <Header as='h3'>
                                <Icon name='clipboard list' />
                                {`${viewedUser.firstName}'s Forms`}
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
                </>
            )}

            <IncidentEditModal
                open={editModalOpen}
                onClose={handleCloseModal}
                formId={editFormId}
                sites={sites}
                incidentFieldOptions={incidentFieldOptions}
                onSaved={() => currentUid && loadData(currentUid)}
            />
        </Container>
    );
};

Monitor.propTypes = {
    sites: PropTypes.array,
    fieldOptions: PropTypes.object,
};

export default Monitor;
