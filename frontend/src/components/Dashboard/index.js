import React, { useState, useEffect } from 'react';
import { Container, Grid, Header } from 'semantic-ui-react';
import StatCard from './StatCard';

const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/$/, '');

const STATS_CONFIG = [
    { key: 'peopleAssisted', label: 'People Assisted', icon: 'users', color: 'green' },
    { key: 'drugsIntoxicated', label: 'Drugs and/or Intoxicated', icon: 'beer', color: 'yellow' },
    { key: 'alone', label: 'Alone', icon: 'male', color: 'blue' },
    { key: 'sexualAssaultRisk', label: 'Sexual Assault Risk', icon: 'exclamation triangle', color: 'orange' },
    { key: 'deEscalatedViolence', label: 'De-escalated Violence', icon: 'shield alternate', color: 'purple' },
    { key: 'welfareChecks', label: 'Welfare Checks', icon: 'clipboard list', color: 'olive' },
    { key: 'reconnections', label: 'Reconnections', icon: 'handshake', color: 'teal' },
    { key: 'escorted', label: 'Escorted', icon: 'shipping fast', color: 'violet' },
    { key: 'firstAid', label: 'First Aid', icon: 'first aid', color: 'red' },
    { key: 'volunteersHours', label: 'Volunteer Hours', icon: 'clock', color: 'pink' },
    { key: 'volunteers', label: 'Volunteer Shifts', icon: 'hand paper', color: 'brown' },
];

const Dashboard = () => {
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_BASE_URL}/api/dashboard`)
            .then((res) => res.json())
            .then((data) => { setStats(data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    return (
        <Container style={{ paddingTop: '2rem' }}>
            <Header as='h1' className='sectionHeader'>
                Welcome to our Dashboard!
            </Header>
            <p style={{ textAlign: 'center', marginBottom: '1.5em', color: '#666' }}>
                This is the difference we've made so far!
            </p>
            <Grid stackable centered>
                {STATS_CONFIG.map((s) => (
                    <StatCard
                        key={s.key}
                        topLabel={s.label}
                        iconName={s.icon}
                        iconColor={s.color}
                        number={stats[s.key] || 0}
                        loading={loading}
                    />
                ))}
            </Grid>
        </Container>
    );
};

export default Dashboard;
