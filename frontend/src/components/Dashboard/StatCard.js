import React from 'react';
import PropTypes from 'prop-types';
import { Grid, Icon, Loader, Segment, Statistic } from 'semantic-ui-react';

const StatCard = ({ topLabel, iconName, iconColor, number, loading }) => {
    return (
        <Grid.Column mobile={16} tablet={8} computer={5} style={{ marginBottom: '1em' }}>
            <Segment color='blue' raised textAlign='center'>
                {loading ? (
                    <Loader active inline='centered' />
                ) : (
                    <Statistic size='small'>
                        <Statistic.Label>{topLabel}</Statistic.Label>
                        <Statistic.Value>
                            <Icon name={iconName} color={iconColor} />
                            {' '}{number != null ? number.toLocaleString() : 0}
                        </Statistic.Value>
                    </Statistic>
                )}
            </Segment>
        </Grid.Column>
    );
};

StatCard.propTypes = {
    topLabel: PropTypes.string.isRequired,
    iconName: PropTypes.string.isRequired,
    iconColor: PropTypes.string.isRequired,
    number: PropTypes.number,
    loading: PropTypes.bool,
};

StatCard.defaultProps = {
    number: 0,
    loading: false,
};

export default StatCard;
