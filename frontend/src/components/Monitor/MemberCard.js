import React from 'react';
import PropTypes from 'prop-types';
import { Grid, Icon, Segment } from 'semantic-ui-react';

const ROLE_CONFIG = {
    administrator: { icon: 'star', color: 'yellow' },
    teamLeader: { icon: 'users', color: 'blue' },
    teamMember: { icon: 'user', color: 'teal' },
};

const MemberCard = ({ member, onClick }) => {
    const cfg = ROLE_CONFIG[member.userLevel] || ROLE_CONFIG.teamMember;
    const fullName = [member.firstName, member.lastName].filter(Boolean).join(' ') || 'Unknown';

    return (
        <Grid.Column mobile={8} tablet={5} computer={4} style={{ marginBottom: '1em' }}>
            <Segment
                raised
                textAlign='center'
                style={{ cursor: 'pointer', minHeight: '120px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}
                onClick={() => onClick(member)}
            >
                <Icon name={cfg.icon} size='big' color={cfg.color} />
                <div style={{ marginTop: '0.5em', fontWeight: 'bold', fontSize: '1.1em' }}>
                    {fullName}
                </div>
                {member.site && (
                    <div style={{ color: '#888', fontSize: '0.85em', marginTop: '0.3em' }}>
                        {member.site}
                    </div>
                )}
            </Segment>
        </Grid.Column>
    );
};

MemberCard.propTypes = {
    member: PropTypes.shape({
        uid: PropTypes.string.isRequired,
        firstName: PropTypes.string,
        lastName: PropTypes.string,
        userLevel: PropTypes.string,
        site: PropTypes.string,
    }).isRequired,
    onClick: PropTypes.func.isRequired,
};

export default MemberCard;
